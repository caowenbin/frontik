# coding=utf-8

"""
Example usage:

if __name__ == '__main__':
    # read configs and process standard options
    tornado_util.server.bootstrap(config_filename)

    tornado_util.server.main(tornado.web.Application(...))
"""

import logging
import os
import time

import tornado.autoreload
import tornado.options
from tornado.options import options

log = logging.getLogger('tornado_util.server')

tornado.options.define('port', 8000, int)
tornado.options.define('config', None, str)
tornado.options.define('host', '0.0.0.0', str)
tornado.options.define('autoreload', True, bool)
tornado.options.define('stop_timeout', 3, int)
tornado.options.define('log_blocked_ioloop_timeout', 0, float)


def bootstrap(config_file, pidfile=None, options_callback=None):
    """
    - define options: config, host, port, daemonize, autoreload
    - read command line options and config file
    - daemonize
    """

    configs_to_read = [config_file] if not isinstance(config_file, (list, tuple)) else config_file

    for config in configs_to_read:
        tornado.options.parse_config_file(config, final=False)

    if callable(options_callback):
        options_callback()

    for config in configs_to_read:
        log.debug('using config: %s', config)
        tornado.autoreload.watch(config)


def main(app, port, on_stop_request=lambda: None, on_ioloop_stop=lambda: None):
    """
    - run server on host:port
    - launch autoreload on file changes
    """

    import tornado.httpserver
    import tornado.ioloop

    def ioloop_is_running():
        return tornado.ioloop.IOLoop.instance()._running

    try:
        log.info('starting server on %s:%s', options.host, port)
        http_server = tornado.httpserver.HTTPServer(app)
        http_server.listen(port, options.host)

        io_loop = tornado.ioloop.IOLoop.instance()
        if tornado.options.options.log_blocked_ioloop_timeout > 0:
            io_loop.set_blocking_log_threshold(tornado.options.options.log_blocked_ioloop_timeout)

        if options.autoreload:
            tornado.autoreload.start(io_loop, 1000)

        def stop_handler(signum, frame):
            log.info('requested shutdown')
            log.info('shutdowning server on %s:%s', options.host, options.port)
            http_server.stop()

            if ioloop_is_running():
                log.info('going down in %s sec', options.stop_timeout)

                def timeo_stop():
                    if ioloop_is_running():
                        log.info('stopping ioloop')
                        tornado.ioloop.IOLoop.instance().stop()
                        log.info('stopped')
                        on_ioloop_stop()

                def add_timeo():
                    tornado.ioloop.IOLoop.instance().add_timeout(time.time() + options.stop_timeout, timeo_stop)

                tornado.ioloop.IOLoop.instance().add_callback(add_timeo)

            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            on_stop_request()

        import signal
        signal.signal(signal.SIGTERM, stop_handler)

        log.debug('IOLOOP STATR')
        io_loop.start()
    except Exception:
        log.exception('failed to start Tornado application')
