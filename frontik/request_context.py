import functools
import logging
import urlparse
import time

def get_to_dispatch(request, field = 'path'):
    if hasattr(request, 're_'+field):
        return getattr(request, 're_'+field)
    return getattr(request, field)

def set_to_dispatch(request, value, field = 'path'):
    setattr(request, 're_'+field, value)

def augment_request(request, match, parse):
    uri = get_to_dispatch(request, 'uri')

    new_uri = (uri[:match.start()] + uri[match.end():])
    split = urlparse.urlsplit(new_uri[:1] +  new_uri[1:].strip('/'))

    set_to_dispatch(request, new_uri, 'uri')
    set_to_dispatch(request, split.path, 'path')
    set_to_dispatch(request, split.query, 'query')

    arguments = match.groupdict()
    for name, value in arguments.iteritems():
        if value:
            request.arguments.setdefault(name, []).extend(parse(value))


class Stats(object):
    def __init__(self):
        self.page_count = 0
        self.http_reqs_count = 0
        self.http_reqs_size_sum = 0
        self.start_time = time.time()

    def next_request_id(self):
        self.page_count += 1
        return self.page_count

stats = Stats()

log = logging.getLogger('frontik.handler')
class ContextFilter(logging.Filter):
    def filter(self, record):
        record.name = '.'.join(filter(None, [record.name, getattr(record, 'request_id', None)]))
        return True
log.addFilter(ContextFilter())


class PageLogger(logging.LoggerAdapter):
    def __init__(self, logger_name, page, handler_name, zero_time):

        class Logger4Adapter(logging.Logger):
            def handle(self, record):
                logging.Logger.handle(self, record)
                log.handle(record)

        logging.LoggerAdapter.__init__(self, Logger4Adapter('frontik.handler'), dict(request_id = logger_name, page = page, handler = handler_name))
        self._time = zero_time
        self.stages = []
        self.page = page
        #backcompatibility with logger
        self.warn = self.warning
        self.addHandler = self.logger.addHandler

    def stage_tag(self, stage):
        self._stage_tag(stage, (time.time() - self._time) * 1000)
        self._time = time.time()

    def _stage_tag(self, stage, time_delta):
        self.stages.append((stage, time_delta))
        self.debug('Stage: {stage}'.format(stage = stage))

    def stage_tag_backdate(self, stage, time_delta):
        self._stage_tag(stage, time_delta)

    def process_stages(self):
        self.debug("Stages for {0} : ".format(self.page) + " ".join(["{0}:{1:.2f}ms".format(k, v) for k, v in self.stages]))

    def process(self, msg, kwargs):
        if "extra" in kwargs:
            kwargs["extra"].update(self.extra)
        else :
            kwargs["extra"] = self.extra
        return msg, kwargs


class RequestContext(object):
    def __init__(self, app, request):
        self.application = app
        self.request = request
        self.request_id = request.headers.get('X-Request-Id', str(stats.next_request_id()))
        self.started = time.time()
        self.log = PageLogger(self.request_id, request.path, "self.__module__", self.started)

    def dispatch_on_url(self, pattern, parse):
        """use with regex (compiled or not) as pattern"""

        match_obj = pattern.match(get_to_dispatch(self.request, 'uri'))
        if match_obj:
            augment_request(self.request, match_obj, parse)
        return match_obj

def in_context(f):
    @functools.wraps(f)
    def wrapper(self, application, request, *a, **kw):
        if not 'context' in kw:
            kw['context'] = RequestContext(application, request)
        return f(self, application, request, *a, **kw)
    return wrapper
