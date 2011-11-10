import weakref
import tornado.options

class WHC(object):
    def __init__(self):
        self.count = 0
        self.zero_listeners = []

    def inc(self):
        self.count += 1

    def dec(self):
        self.count -= 1
        if not self.count:
            for listener in self.zero_listeners:
                listener()
            self.zero_listeners = []

    def subscribe(self, whom):
        if self.count:
            self.zero_listeners.append(whom)
        else:
            whom()

    def __repr__(self):
        return "workers count = %s" % self.count

working_handlers_counter = WHC()

class PageHandlerWHCLimit(object):
    def __init__(self, handler):
        self.handler = weakref.proxy(handler)

        # working handlers count
        global working_handlers_counter
        self.acquired = False # init it with false in case of emergency failure

        if working_handlers_counter.count <= tornado.options.options.handlers_count:
            self.handler.log.info('started %s (%s)',
                                  self.handler._request_summary(),
                                  working_handlers_counter)
        else:
            self.handler.log.warn('dropping %s; too many workers (%s)',
                                  self.handler._request_summary(),
                                  working_handlers_counter)
            raise tornado.web.HTTPError(503)

        self.acquire()

    def acquire(self):
        if not self.acquired:
            global working_handlers_counter
            self.acquired = True
            working_handlers_counter.inc()
            self.handler.log.info('INC %s', working_handlers_counter)

    def release(self):
        if self.acquired:
            global working_handlers_counter
            self.acquired = False
            working_handlers_counter.dec()
            self.handler.log.info('DEC %s', working_handlers_counter)

