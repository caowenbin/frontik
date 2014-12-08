# coding=utf-8

import tornado.concurrent


class Future(tornado.concurrent.Future):
    # deprecated synonym
    set_data = tornado.concurrent.Future.set_result

    # deprecated synonym
    get = tornado.concurrent.Future.result
