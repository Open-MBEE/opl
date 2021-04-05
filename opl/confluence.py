import atlassian

class Confluence:
    def __init__(self, server, username, password):
        self._y_confluence = atlassian.Confluence(
            url=server,
            username=username,
            password=password,
        )

    def page(self, page_id):
        return self._Page(self, page_id);


    class _Page:
        _s_title = None

        def __init__(self, k_wiki, si_page):
            self._k_wiki = k_wiki
            self._y_confluence = k_wiki._y_confluence
            self._si_page = si_page

        def get_content(self):
            _g_page = self._y_confluence.get_page_by_id(self._si_page, expand=('body.storage'))
            self._s_title = _g_page['title']
            return _g_page['body']['storage']['value']

        def update_content(self, content):
            # page title not set; download it
            if self._s_title is None:
                self._s_title = self._y_wiki.get_page_by_id(si_page)['title']

            # update page content
            return self._y_confluence.update_page(
                type='page',
                page_id=self._si_page,
                title=self._s_title,
                body=content,
                minor_edit=True,
            )

