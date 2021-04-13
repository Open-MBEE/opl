import atlassian

class _Page:
    '''
    Created by using the `.page()` method on a `Confluence` instance
    '''
    _s_title = None
    _g_version = None

    def __init__(self, k_wiki, si_page: str):
        self._k_wiki = k_wiki
        self._y_confluence = k_wiki._y_confluence
        self._si_page = si_page

    @property
    def version(self):
        if self._g_version is None:
            self.get_content()
        return self._g_version

    def get_content(self) -> str:
        '''
        Retrieve the XHTML content of the page
        '''
        _g_page = self._y_confluence.get_page_by_id(self._si_page, expand='body.storage,version')
        self._g_version = _g_page['version']
        self._s_title = _g_page['title']
        return _g_page['body']['storage']['value']

    def update_content(self, content: str):
        '''
        Update the XHTML content of the page
        '''
        # page title not set; download it
        if self._s_title is None:
            self._s_title = self._k_wiki.get_page_by_id(self._si_page)['title']

        # update page content
        return self._y_confluence.update_page(
            type='page',
            page_id=self._si_page,
            title=self._s_title,
            body=content,
            minor_edit=True,
        )


class Confluence:
    '''
    Create a new client to interact with Confluence

    :param server: URI of the Confluence server
    :param username: Username to authenticate with
    :param password: Password to authenticate with
    '''
    def __init__(self, server: str, username: str, password: str):
        self._y_confluence = atlassian.Confluence(
            url=server,
            username=username,
            password=password,
        )

    def page(self, page_id: str) -> _Page:
        '''
        Create a handle for a specific page

        :param page_id: the ID of the page
        '''
        return _Page(self, page_id);

