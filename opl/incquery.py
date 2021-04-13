import re
import uuid
import html
import datetime
from urllib.parse import urlparse
from typing import Optional, Callable, List, Dict, Any, NamedTuple

from .types import Hash
import iqs_client

# type aliases
Row = Dict[str, Any]
Rewriters = Dict[str, Callable[[Any], str]]


# connector-specific extensions may add custom ways to convert a dict to an element representation;
#     parse a dict and return the constructed element or None if not the right format
#     default is ElementInCompartmentDescriptor
d_element_dict_recognizers : List[Callable[[dict], Optional[Any]]] = []

# borrowed from https://github.com/IncQueryLabs/incquery-server-jupyter/blob/5c869a3436f94b370e80e2431e5187974317e5b9/source/incqueryserver-jupyter/iqs_jupyter/helpers.py#L34-L45
def _dict_to_element(z_dict_or_attribute_value, f_url_provider=None):
    if isinstance(z_dict_or_attribute_value, dict):
        for f_recognizer in d_element_dict_recognizers:
            g_recognized = f_recognizer(z_dict_or_attribute_value)
            if g_recognized:
                if f_url_provider is not None:
                    g_recognized.url = f_url_provider(g_recognized)
                return g_recognized
        # not recognized as an element, treated as raw dict
        return z_dict_or_attribute_value
    else:
        return z_dict_or_attribute_value


# convert dict of [name: str => pattern_body: str] to the expected format used by API client
def _dict_to_query_defs(h_queries: Hash):
    a_defs = []
    for s_name, s_query in h_queries.items():
        m_name = re.match(r'\s*(?:private\s+)?(?:search\s+|incremental\s+)?pattern\s+([^\s\(]+)\s*\(', s_query)
        s_prepend = ''
        if m_name is None:
            s_prepend = f'pattern {s_name}'
        elif s_name != m_name.group(1):
            raise Exception(f'pattern definition for "{s_name}" must have identical pattern name, instead found "{m_name.group(1)}"')
        a_defs.append(s_prepend+s_query)

    return a_defs


# convert dict of [parameter: str => value: str] to the expected format used by API client
def _dict_to_bindings(h_bindings: Hash):
    return [
        {'parameter':si_param, 'value':w_value} for si_param, w_value in h_bindings.items()
    ]


class QueryField(NamedTuple):
    '''
    Descriptor for a query field to be used for extending a query result row
    '''
    join: Callable[[Hash], Hash]
    query: str
    select: Callable[[Hash], str]
    bindings: Hash={}
    patterns: Hash={}


class IncQueryProject:
    '''
    Create a new client to query a specific IncQuery project. May either
    provide the full compartment IRI or an org, project ID and ref to
    automatically select the latest commit.

    :param server: URI of the IncQuery server
    :param username: Username to authenticate with
    :param password: Password to authenticate with
    :param org: MMS org of the project to select
    :param project: MMS project ID of the project to select
    :param ref: Which ref to select from the project; defaults to 'master'. Loads the latest commit from that ref
    :param compartment: Instead of specifying org, project/ref, use the specified compartment IRI
    :param patterns: Default patterns to use for implicit query executions
    '''
    def __init__(self, server: str, username: str, password: str, org: str=None, project: str=None, ref: str=None, compartment: str=None, patterns: Hash={}):

        # parse server iri
        du_iqs = urlparse(server)

        # instantiate iqs_client API client
        self._y_incquery = iqs_client.ApiClient(iqs_client.Configuration(
            host=du_iqs.scheme + '://' + du_iqs.netloc + '/api',
            username=username,
            password=password,
        ))

        # instantiate API groups
        self._y_incquery_queries = iqs_client.QueriesApi(self._y_incquery)
        self._y_incquery_query_execution = iqs_client.QueryExecutionApi(self._y_incquery)
        self._y_incquery_in_memory = iqs_client.InMemoryIndexApi(self._y_incquery)
        self._y_incquery_persistent = iqs_client.PersistentIndexApi(self._y_incquery)
        self._y_incquery_mms_repo = iqs_client.MmsRepositoryApi(self._y_incquery)
        self._y_incquery_demo = iqs_client.DemoApi(self._y_incquery)

        # save patterns dict
        self._h_patterns = patterns

        # project id specified
        if project is not None:
            if org is None:
                raise Exception('must at least provide an org ID and project ID')
            if compartment is not None:
                raise Exception('if a project/ref is provided then compartment must be None')

            # select latest commit
            self._s_compartment = self._latest_commit(org, project, ref)
        # org id specified
        elif org is not None:
            raise Exception('must at least provide an org ID and project ID')
        # compartment IRI specified
        elif compartment is not None:
            self._s_compartment = compartment
        # neither specified
        else:
            raise Exception('must specify either a project or compartment')

        # ensure the selected compartment is loaded into in-memory index
        self._y_incquery_in_memory.load_model_compartment({
            'compartmentURI': self._s_compartment,
        })

    # determines the latest available commit for a given org/project/ref
    def _latest_commit(self, si_org: str, si_project: str, s_ref: str=None):
        if s_ref is None: s_ref = 'master'

        # prepare compartment URI prefix
        s_prefix = f'mms-index:/orgs/{si_org}/projects/{si_project}/refs/{s_ref}/commits/'

        # prep latest fields
        d_latest_commit = None
        p_latest_compartment = None

        # each compartment stored in persistent index
        for g_persistent_compartment in self._y_incquery_persistent.list_persisted_model_compartments().persisted_model_compartments:
            p_persistent_compartment = g_persistent_compartment.compartment_uri

            # compartment URI matches prefix target
            if p_persistent_compartment.startswith(s_prefix):
                # fetch compartment details
                g_details_compartment = self._y_incquery_mms_repo.get_repository_compartment_details(g_persistent_compartment)

                # parse compartment datetime
                d_commit = datetime.datetime.strptime(g_details_compartment.commit_name, '%Y-%m-%d %H:%M:%S')

                # latest by default or newer; make it latest
                if p_latest_compartment is None or d_commit > d_latest_commit:
                    d_latest_commit = d_commit
                    p_latest_compartment = p_persistent_compartment

        # return compartment URI to latest commit
        return p_latest_compartment


    def execute(self, name: str, patterns: Hash={}, bindings: Row={}, w_url_provider=None) -> List[Row]:
        '''
        Execute a query and return the results as a list of dicts

        :param name: Name of which pattern to execute
        :param bindings: A dict of bindings to pass into query execution
        :param patterns: A dict of patterns to include during query execution (overwrites defaults provided to constructor)
        '''
        si_query = name
        h_patterns = {**self._h_patterns}
        if patterns is not None:
            h_patterns.update(patterns)
        h_bindings = bindings

        # execute query
        g_response = self._y_incquery_demo.execute_query_one_off({
            'modelCompartment': {
                'compartmentURI': self._s_compartment,
            },
            'queryLanguage': 'viatra',
            'queryName': si_query,
            'queryDefinitions': _dict_to_query_defs(h_patterns),
            'parameterBinding': _dict_to_bindings(h_bindings),
        })

        # return results as list of dicts
        return [
            dict(
                (g_arg.parameter, _dict_to_element(g_arg.value, w_url_provider)) for g_arg in g_match.arguments
            ) for g_match in g_response.matches
        ]


    def extend_row(self, row: Row, query_field: QueryField) -> List[Row]:
        '''
        Extend a row by applying the given query_field

        :param row: A dict item obtained from the list of `execute` results
        :param query_field: A QueryField descriptor that specifies how to perform the extension
        '''
        g_row = row
        k_field = query_field

        # ref bindings dict
        h_bindings = k_field.bindings

        # upsert with bindings from applying field join
        h_bindings.update(k_field.join(g_row))

        # execute query
        a_rows = self.execute(
            name=k_field.query,
            bindings=h_bindings,
            patterns=k_field.patterns,
        )

        # map thru select function
        return list(map(k_field.select, a_rows))



class QueryResultsTable:
    '''
    Create the means to render the query results as a table

    :param rows: The list of rows returned from executing a query
    :param labels: A dict that maps field IDs to text labels
    '''
    def __init__(self, rows: List[Row], labels: Hash=None, rewriters: Rewriters={}):
        self._a_rows = rows
        self._h_labels = labels
        self._h_rewriters = rewriters or {}

    @property
    def rows(self):
        return self._a_rows

    @property
    def labels(self):
        return self._h_labels

    @property
    def rewriters(self):
        return self._h_rewriters

    def to_html(self, rewriters: Rewriters={}) -> str:
        '''
        Construct an HTML table to render the table

        :param rewriters: dict of callback functions for rewriting cell values under the given columns
        '''
        rewriters = rewriters or {}
        h_rewriters = {**self._h_rewriters, **rewriters}
        s_html = '<table><tbody><tr>'
        h_labels = {**self._h_labels}

        # empty results
        if 0 == len(self._a_rows):
            # no labels provided; exit
            if self._h_labels is None:
                return '<p>No query results and no column headers were provided. Nothing to display.</p>'
        # non-empty results
        else:
            # each column in first row
            for si_col in self._a_rows[0]:
                # column id missing from labels; default to id
                if si_col not in h_labels:
                    h_labels[si_col] = si_col

        # construct headers
        for si_col in self._h_labels:
            s_html += '<th>{label}</th>'.format(label=self._h_labels[si_col])

        # close header row
        s_html += '</tr>'

        # construct data
        for g_row in self._a_rows:
            s_html += '<tr>'
            for si_col in self._h_labels:
                z_value = g_row[si_col]
                s_cell = ''

                # column has rewriter
                if si_col in h_rewriters:
                    s_cell += h_rewriters[si_col](z_value, g_row)
                # value is a list
                elif isinstance(z_value, list):
                    s_cell += '<ul>'
                    for s_value in z_value:
                        s_cell += '<li>{value}</li>'.format(value=html.escape(s_value))
                    s_cell += '</ul>'
                # write simple string as HTML
                else:
                    s_cell += html.escape(z_value)
                # style="text-align:left;"
                s_html += '<td>{value}</td>'.format(value=s_cell)
            s_html += '</tr>'

        # close
        return s_html+'</tbody></table>'

    def to_confluence_xhtml(self, span_id: str, macro_id: str=None, rewriters: Rewriters={}):
        '''
        Construct an XHTML table to render the table in Confluence

        :param span_id: the ID to give the annotated span
        :param macro_id: optional UUIDv4 to give the Confluence macro
        :param rewriters: dict of callback functions for rewriting cell values under the given columns
        '''
        return '''
            <ac:structured-macro ac:name="span" ac:schema-version="1" ac:macro-id="{macro_id}">
                <ac:parameter ac:name="id">{span_id}</ac:parameter>
                <ac:parameter ac:name="atlassian-macro-output-type">INLINE</ac:parameter>
                <ac:rich-text-body>
                    <p class="auto-cursor-target">
                        <br />
                    </p>
                    {content}
                    <p class="auto-cursor-target">
                        <br />
                    </p>
                </ac:rich-text-body>
            </ac:structured-macro>
        '''.format(
            macro_id=macro_id or str(uuid.uuid4()),
            span_id=span_id,
            content=self.to_html(rewriters),
        )
