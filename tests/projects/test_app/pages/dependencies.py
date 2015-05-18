# coding=utf-8

from tornado.concurrent import Future

from frontik.handler import HTTPError, PageHandler


def dep1(handler):
    handler.run.append('dep1')
    f = Future()
    f.set_result(None)
    return f


@PageHandler.dependency(dep1)
def dep2(handler):
    handler.run.append('dep2')

    if handler.get_argument('fail', 'false') == 'true':
        raise HTTPError(403, json={'reason': 'failed in dependency'})

    f = Future()
    f.set_result(None)
    return f


@PageHandler.dependency(dep1)
def dep3(handler):
    handler.run.append('dep3')


@PageHandler.dependency(dep2, dep3)
def dep4(handler):
    handler.run.append('dep4')
    f = Future()
    f.set_result(None)
    return f


@PageHandler.dependency(dep4)
def dep5(handler):
    handler.run.append('dep5')
    f = Future()
    f.set_result(None)
    return f


class Page(PageHandler):
    def __init__(self, application, request, logger, **kwargs):
        super(Page, self).__init__(application, request, logger, **kwargs)
        self.run = []

    @PageHandler.depends(dep4)
    def get_page(self):
        self.text = ' '.join(self.run)
