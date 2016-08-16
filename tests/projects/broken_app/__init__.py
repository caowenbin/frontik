# coding=utf-8

from tornado.concurrent import Future

from frontik.app import FrontikApplication


class TestApplication(FrontikApplication):
    def init_async(self):
        future = Future()
        future.set_exception(Exception('Failed to initialize'))
        return future
