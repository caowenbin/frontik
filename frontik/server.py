#!/usr/bin/env python
# coding=utf-8

import logging
import sys

from tornado.options import options

import frontik.app
from frontik.frontik_logging import configure_logging
from frontik.launcher import server
import frontik.options

log = logging.getLogger('frontik.server')


def main(config_file=None, port=None, pidfile=None):

    from zmq.eventloop import ioloop
    ioloop.install()

    server.bootstrap(config_file=config_file, options_callback=configure_logging, pidfile=None)

    try:
        if options.app is None:
            log.exception('no frontik application present (`app` option is not specified)')
            sys.exit(1)

        tornado_app = frontik.app.get_tornado_app(
            options.app_root_url, frontik.app.App(options.app), options.tornado_settings
        )
    except:
        log.exception('failed to initialize frontik application, quitting')
        sys.exit(1)

    server.main(tornado_app, port if port is not None else options.port)
