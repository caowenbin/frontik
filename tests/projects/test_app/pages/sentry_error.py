# coding=utf-8

from functools import partial

from tornado.ioloop import IOLoop

from frontik.handler import HTTPError, PageHandler


class Page(PageHandler):
    def get_page(self):
        raise Exception('Runtime exception for Sentry')

    def post_page(self):
        raise HTTPError('HTTPError for Sentry')

    def write_error(self, status_code=500, **kwargs):
        # delay page finish to make sure that sentry mock got the exception
        self.add_timeout(IOLoop.instance().time() + 1.0, partial(super(Page, self).write_error, status_code, **kwargs))
