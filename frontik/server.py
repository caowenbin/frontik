#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging
import sys
import time

import tornado.options
import tornado_util.server
from tornado.options import options
import tornado.ioloop

import frontik.app
import frontik.options
import frontik.handler_whc_limit

log = logging.getLogger("frontik.server")

def main(config_file="/etc/frontik/frontik.cfg"):
    tornado_util.server.bootstrap(config_file=config_file)

    if tornado.options.options.syslog:
        syslog_handler = logging.handlers.SysLogHandler(
            facility=logging.handlers.SysLogHandler.facility_names[tornado.options.options.syslog_facility],
            address=tornado.options.options.syslog_address)
        syslog_handler.setFormatter(
            logging.Formatter("[%(process)s] %(asctime)s %(levelname)s %(name)s: %(message)s"))
        logging.getLogger().addHandler(syslog_handler)

    for log_channel_name in options.suppressed_loggers:
        logging.getLogger(log_channel_name).setLevel(logging.WARN)

    try:
        app = frontik.app.get_app(options.urls, options.apps)
    except:
        log.exception("failed to initialize frontik.app, quitting")
        sys.exit(1)

    def on_server():
        log.info('Pending %s', frontik.handler_whc_limit.working_handlers_counter)
        def whc_listen():
            def stop():
                log.info('No pending workers - graceful down')
                tornado.ioloop.IOLoop.instance().stop()
            tornado.ioloop.IOLoop.instance().add_callback(stop)
        frontik.handler_whc_limit.working_handlers_counter.subscribe(whc_listen)

    def on_ioloop():
        log.info('Left wo response: %s', frontik.handler_whc_limit.working_handlers_counter)
        
    tornado_util.server.main(app, on_server, on_ioloop)
