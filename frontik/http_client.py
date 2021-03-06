# coding=utf-8

from collections import namedtuple
from functools import partial
import re
import time

import pycurl
import simplejson
from lxml import etree
from tornado.concurrent import Future
from tornado.curl_httpclient import CurlAsyncHTTPClient
from tornado.options import options

from frontik.async import AsyncGroup
from frontik.auth import DEBUG_AUTH_HEADER_NAME
from frontik.compat import iteritems
from frontik.debug import DEBUG_HEADER_NAME, response_from_debug
import frontik.util


class HttpClient(object):
    def __init__(self, handler, http_client_impl, modify_http_request_hook):
        self.handler = handler
        self.modify_http_request_hook = modify_http_request_hook
        self.http_client_impl = http_client_impl

    def group(self, futures, callback=None, name=None):
        if callable(callback):
            results_holder = {}
            group_callback = self.handler.finish_group.add(self.handler.check_finished(callback, results_holder))

            async_group = AsyncGroup(group_callback, name=name)

            def future_callback(name, future):
                results_holder[name] = future.result()

            for name, future in iteritems(futures):
                if future.done():
                    future_callback(name, future)
                else:
                    self.handler.add_future(future, async_group.add(partial(future_callback, name)))

            async_group.try_finish_async()

        return futures

    def get_url(self, url, data=None, headers=None, connect_timeout=None, request_timeout=None,
                callback=None, follow_redirects=True, labels=None,
                add_to_finish_group=True, parse_response=True, parse_on_error=False):

        future = Future()
        request = frontik.util.make_get_request(url, data, headers, connect_timeout, request_timeout, follow_redirects)
        request._frontik_labels = labels

        self.fetch(
            request,
            partial(self._parse_response, future, callback, parse_response, parse_on_error),
            add_to_finish_group=add_to_finish_group
        )

        return future

    def head_url(self, url, data=None, headers=None, connect_timeout=None, request_timeout=None,
                 callback=None, follow_redirects=True, labels=None,
                 add_to_finish_group=True):

        future = Future()
        request = frontik.util.make_head_request(url, data, headers, connect_timeout, request_timeout, follow_redirects)
        request._frontik_labels = labels

        self.fetch(
            request,
            partial(self._parse_response, future, callback, False, False),
            add_to_finish_group=add_to_finish_group
        )

        return future

    def post_url(self, url, data='', headers=None, files=None, connect_timeout=None, request_timeout=None,
                 callback=None, follow_redirects=True, content_type=None, labels=None,
                 add_to_finish_group=True, parse_response=True, parse_on_error=False):

        future = Future()
        request = frontik.util.make_post_request(
            url, data, headers, files, content_type, connect_timeout, request_timeout, follow_redirects
        )
        request._frontik_labels = labels

        self.fetch(
            request,
            partial(self._parse_response, future, callback, parse_response, parse_on_error),
            add_to_finish_group=add_to_finish_group
        )

        return future

    def put_url(self, url, data='', headers=None, connect_timeout=None, request_timeout=None,
                callback=None, content_type=None, labels=None,
                add_to_finish_group=True, parse_response=True, parse_on_error=False):

        future = Future()
        request = frontik.util.make_put_request(url, data, headers, content_type, connect_timeout, request_timeout)
        request._frontik_labels = labels

        self.fetch(
            request,
            partial(self._parse_response, future, callback, parse_response, parse_on_error),
            add_to_finish_group=add_to_finish_group
        )

        return future

    def delete_url(self, url, data=None, headers=None, connect_timeout=None, request_timeout=None,
                   callback=None, content_type=None, labels=None,
                   add_to_finish_group=True, parse_response=True, parse_on_error=False):

        future = Future()
        request = frontik.util.make_delete_request(url, data, headers, content_type, connect_timeout, request_timeout)
        request._frontik_labels = labels

        self.fetch(
            request,
            partial(self._parse_response, future, callback, parse_response, parse_on_error),
            add_to_finish_group=add_to_finish_group
        )

        return future

    def fetch(self, request, callback, add_to_finish_group=True):
        """ Tornado HTTP client compatible method """
        if self.handler._finished:
            self.handler.log.warning(
                'attempted to make http request to %s when page is finished, ignoring', request.url
            )

            return Future()

        if self.handler.debug_mode.pass_debug:
            request.headers[DEBUG_HEADER_NAME] = 'true'

            # debug_timestamp is added to avoid caching of debug responses
            request.url = frontik.util.make_url(request.url, debug_timestamp=int(time.time()))

            for header_name in ('Authorization', DEBUG_AUTH_HEADER_NAME):
                authorization = self.handler.request.headers.get(header_name)
                if authorization is not None:
                    request.headers[header_name] = authorization

        request.headers['X-Request-Id'] = self.handler.request_id

        if request.connect_timeout is None:
            request.connect_timeout = options.http_client_default_connect_timeout
        if request.request_timeout is None:
            request.request_timeout = options.http_client_default_request_timeout

        request.connect_timeout *= options.timeout_multiplier
        request.request_timeout *= options.timeout_multiplier

        def req_callback(response):
            response = self._log_response(request, response)

            if callable(callback):
                callback(response)

        if add_to_finish_group:
            req_callback = self.handler.finish_group.add(self.handler.check_finished(req_callback))

        if options.http_proxy_host is not None:
            request.proxy_host = options.http_proxy_host
            request.proxy_port = options.http_proxy_port

        if isinstance(self.http_client_impl, CurlAsyncHTTPClient):
            request.prepare_curl_callback = partial(
                self._prepare_curl_callback, next_callback=request.prepare_curl_callback
            )

        return self.http_client_impl.fetch(self.modify_http_request_hook(request), req_callback)

    def _prepare_curl_callback(self, curl, next_callback):
        curl.setopt(pycurl.NOSIGNAL, 1)

        if callable(next_callback):
            next_callback(curl)

    def _log_response(self, request, response):
        try:
            debug_extra = {}
            if response.headers.get(DEBUG_HEADER_NAME):
                debug_response = response_from_debug(request, response)
                if debug_response is not None:
                    debug_xml, response = debug_response
                    debug_extra['_debug_response'] = debug_xml

            if self.handler.debug_mode.enabled:
                debug_extra.update({'_response': response, '_request': request})
                if getattr(request, '_frontik_labels', None) is not None:
                    debug_extra['_labels'] = request._frontik_labels

            log_message = 'got {code}{size} {url} in {time:.2f}ms'.format(
                code=response.code,
                url=response.effective_url,
                size=' {0} bytes'.format(len(response.body)) if response.body is not None else '',
                time=response.request_time * 1000
            )

            log_method = self.handler.log.warn if response.code >= 500 else self.handler.log.info
            log_method(log_message, extra=debug_extra)

        except Exception:
            self.handler.log.exception('Cannot log response info')

        return response

    def _parse_response(self, future, callback, parse_response, parse_on_error, response):
        data = None
        result = RequestResult()

        try:
            if response.error and not parse_on_error:
                self._set_response_error(response)
            elif not parse_response:
                data = response.body
            elif response.code != 204:
                content_type = response.headers.get('Content-Type', '')
                for k, v in iteritems(DEFAULT_REQUEST_TYPES):
                    if k.search(content_type):
                        data = v(response, logger=self.handler.log)
                        break
        except FailedRequestException as ex:
            result.set_exception(ex)

        if callable(callback):
            callback(data, response)

        result.set(data, response)
        future.set_result(result)

    def _set_response_error(self, response):
        log_func = self.handler.log.error if response.code >= 500 else self.handler.log.warning
        log_func('{code} failed {url} ({reason!s})'.format(
            code=response.code, url=response.effective_url, reason=response.error)
        )

        raise FailedRequestException(reason=str(response.error), code=response.code)


class FailedRequestException(Exception):
    def __init__(self, **kwargs):
        self.attrs = kwargs


class RequestResult(object):
    __slots__ = ('data', 'response', 'exception')

    ResponseData = namedtuple('ResponseData', ('data', 'response'))

    def __init__(self):
        self.data = None
        self.response = None
        self.exception = None

    def set(self, data, response):
        self.data = data
        self.response = response

    def set_exception(self, exception):
        self.exception = exception


def _parse_response(response, logger, parser=None, response_type=None):
    try:
        return parser(response.body)
    except:
        _preview_len = 100

        if len(response.body) > _preview_len:
            body_preview = '{0}...'.format(response.body[:_preview_len])
        else:
            body_preview = response.body

        logger.exception('failed to parse {0} response from {1}, bad data: "{2}"'.format(
            response_type, response.effective_url, body_preview))

        raise FailedRequestException(url=response.effective_url, reason='invalid {0}'.format(response_type))


_xml_parser = etree.XMLParser(strip_cdata=False)
_parse_response_xml = partial(_parse_response,
                              parser=lambda x: etree.fromstring(x, parser=_xml_parser),
                              response_type='XML')

_parse_response_json = partial(_parse_response,
                               parser=simplejson.loads,
                               response_type='JSON')

DEFAULT_REQUEST_TYPES = {
    re.compile('.*xml.?'): _parse_response_xml,
    re.compile('.*json.?'): _parse_response_json,
    re.compile('.*text/plain.?'): (lambda response, logger: response.body),
}
