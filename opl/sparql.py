import re
import rdflib
from typing import Any, List, Dict

from SPARQLWrapper import SPARQLWrapper, JSON, POST, RDFXML, TURTLE

from .constants import prefixes
from .types import Hash

def _join_prefixes(s_token, s_term=''):
    return '\n'.join([s_token+' '+si_prefix+': <'+p_iri+'>'+s_term for si_prefix, p_iri in prefixes.items()])

S_PREFIXES_SPARQL = _join_prefixes('prefix')
SB_PREFIXES_TURTLE = _join_prefixes('@prefix', ' .').encode()

# regex pattern builder for matching inline directives (i'm not sorry)
def _directive(s_keyword: str, z_arg='', b_capture_indent=False):
    return (
        r'(?m)^'
        ''+(r'([ \t]*)' if b_capture_indent else r'[ \t]*')+''
        r'#[ \t]*'+s_keyword+''
        ''+(r'[ \t]+([\w]+)' if z_arg is True else z_arg or '')+''
        r'[ \t]*$'
    )


class Sparql:
    '''
    Wrapper class to simplify submitting and fetching SPARQL queries

    :param endpoint: full URL to the SPARQL endpoint
    '''
    def __init__(self, endpoint: str):
        '''
        :param endpoint: full URI (with port and path) to SPARQL endpoint
        '''
        self._p_endpoint = endpoint
        self._y_store = SPARQLWrapper(self._p_endpoint)

    @staticmethod
    def load(template: str, variables: Hash={}, injections: Hash={}) -> str:
        '''
        Static method to apply mixins, variable substitions, and injections to a query template string.

        :param template: the SPARQL query template string
        :param variables: dict of variables and their values
        :param injections: dict of injections to apply across query template
        :return: the output query string
        '''
        sx_template = template
        h_vars = variables or {}
        h_injections = injections or {}

        # each def
        sr_def = r'(?s)'+_directive('@def', True)+r'(.*?)'+_directive('@end')
        di_defs = re.finditer(sr_def, sx_template)
        for m_def in di_defs:
            # ref var name
            si_var = m_def.group(1)

            # extract mixin bgp
            sx_mixin = re.sub(r'(?is)^\s*ask\s*\{\s*(.*)\s*\}\s*$', r'\1', m_def.group(2))

            # normalize indentation
            s_init = re.match(r'^[^\n]*\r?\n([ \t]+)', sx_mixin).group(1)
            sx_mixin = re.sub(r'(?m)^'+s_init, '', sx_mixin)

            # remove from template
            sx_template = sx_template.replace(m_def.group(0), '')

            # replace all invocations
            di_invocations = re.finditer(_directive('@mixin', r'[ \t]+'+si_var, True), sx_template)
            for m_invocation in di_invocations:
                s_indent = m_invocation.group(1)
                sx_aligned = re.sub(r'(?m)^', s_indent, sx_mixin)
                sx_template = sx_template.replace(m_invocation.group(0), sx_aligned)

        # injections
        di_inject = re.finditer(_directive('@inject', r'[ \t]+\$([\w]+)', True), sx_template)
        for m_inject in di_inject:
            # ref injection label
            si_inject = m_inject.group(2)

            # injection not declared
            if si_inject not in h_injections:
                continue

            # apply injection(s)
            sx_template = sx_template.replace(m_inject.group(0), m_inject.group(1)+h_injections[si_inject])

        # IRI variables
        di_vars = re.finditer(r'<\$(\w+)>', sx_template)
        for m_vars in di_vars:
            si_var = m_vars.group(1)

            # variable not defined
            if si_var not in h_vars:
                raise Exception(f'query template requires a value for the variable "{si_var}"')

            # replace
            sx_template = sx_template.replace(m_vars.group(0), rdflib.URIRef(h_vars[si_var]).n3())

        # return output query string
        return sx_template.strip()

    def _set_query(self, s_query):
        self._y_store.setQuery(S_PREFIXES_SPARQL+'\n'+s_query)
        self._y_store.addParameter('infer', 'false')
        self._y_store.addParameter('sameAs', 'false')

    def _submit(self):
        try:
            return self._y_store.query()
        except Exception as e_query:
            raise Exception(f'while querying """\n{S_PREFIXES_SPARQL}\n{s_query}"""') from e_query

    def construct(self, query: str) -> str:
        '''
        Submit a SPARQL CONSTRUCT query and return the resulting graph as a Turtle document string

        :param query: the SPARQL CONSTRUCT query string to submit. Prefixes are prepended automatically
        '''
        self._set_query(query)
        self._y_store.setReturnFormat(TURTLE)

        self._y_store.addCustomHttpHeader('Accept', 'text/turtle')

        self._y_store.setMethod(POST)

        y_results = self._submit();

        # a_results = self._y_store.query()
        return SB_PREFIXES_TURTLE+y_results.convert()

    def fetch(self, query: str) -> List[Dict[str, Any]]:
        '''
        Submit a SPARQL SELECT query and return the query result rows as a list of dicts

        :param query: the SPARQL SELECT query string to submit. Prefixes are prepended automatically
        '''
        self._set_query(query)
        self._y_store.setReturnFormat(JSON)

        self._y_store.setMethod(POST)

        y_results = self._submit()

        return y_results.convert()['results']['bindings']

