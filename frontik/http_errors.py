# coding=utf-8

import httplib
import tornado.web


# Additional HTTP Status Codes according to http://tools.ietf.org/html/rfc6585
PRECONDITION_REQUIRED = 428
TOO_MANY_REQUESTS = 429
REQUEST_HEADER_FIELDS_TOO_LARGE = 431
NETWORK_AUTHENTICATION_REQUIRED = 511

_additional_response_codes = {
    PRECONDITION_REQUIRED: 'Precondition Required',
    TOO_MANY_REQUESTS: 'Too Many Requests',
    REQUEST_HEADER_FIELDS_TOO_LARGE: 'Request Header Fields Too Large',
    NETWORK_AUTHENTICATION_REQUIRED: 'Network Authentication Required',
}


def process_status_code(status_code, reason=None):
    if status_code not in httplib.responses:
        if status_code in _additional_response_codes:
            # autoset reason for extended HTTP codes
            reason = reason if reason is not None else _additional_response_codes[status_code]
        else:
            # change error code for unknown HTTP codes (ex. fake 599 error code)
            status_code = httplib.SERVICE_UNAVAILABLE
            reason = None
    return status_code, reason


class HTTPError(tornado.web.HTTPError):
    """
    Extends tornado.web.HTTPError with several keyword-only arguments.
    Also allow using some extended HTTP codes

    :arg dict headers: Custom HTTP headers to pass along with the error response.
    :arg string text: Plain text override for error response.
    :arg etree xml: XML node to be added to `self.doc`. If present, error page will be
        produced with `application/xml` content type.
    :arg dict json: JSON dict to be used as error response. If present, error page
        will be produced with `application/json` content type.
    """
    def __init__(self, status_code, log_message=None, *args, **kwargs):
        headers = kwargs.pop('headers', {})
        for data in ('text', 'xml', 'json'):
            setattr(self, data, kwargs.pop(data, None))

        status_code, kwargs['reason'] = process_status_code(status_code, kwargs.get('reason'))
        super(HTTPError, self).__init__(status_code, log_message, *args, **kwargs)
        self.headers = headers


class BackendFailedError(HTTPError):
    DEFAULT_ERROR_CODE = httplib.BAD_GATEWAY

    def __init__(self, backend_response, log_message, proxy_codes=('1xx', '3xx', '4xx'), *args, **kwargs):
        if not backend_response.error:
            super(BackendFailedError, self).__init__(self.DEFAULT_ERROR_CODE, log_message, *args, **kwargs)

        elif str(backend_response.code % 100) in (x[0] for x in proxy_codes):
            super(BackendFailedError, self).__init__(backend_response.code, log_message, *args, **kwargs)

        super(BackendFailedError, self).__init__(self.DEFAULT_ERROR_CODE, log_message, *args, **kwargs)
