from frontik.handler import PageHandler


def simple_preprocessor(handler, callback):
    callback()


class Page(PageHandler):
    @PageHandler.add_preprocessor(*([simple_preprocessor] * 100))
    def get_page(self):
        pass

    def compute_etag(self):
        return None
