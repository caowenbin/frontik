# coding=utf-8

import json

from frontik.future import Future
from frontik.http_client import RequestResult


def _check_value(v):
    def _check_iterable(l):
        return [_check_value(v) for v in l]

    def _check_dict(d):
        return {k: _check_value(v) for k, v in d.iteritems()}

    if isinstance(v, dict):
        return _check_dict(v)
    elif isinstance(v, (set, frozenset, list, tuple)):
        return _check_iterable(v)
    elif isinstance(v, RequestResult):
        if v.exception is not None:
            return JsonBuilder.get_error_node(v.exception)
        return _check_value(v.data)
    elif isinstance(v, Future):
        return _check_value(v.result())
    elif isinstance(v, JsonBuilder):
        return _check_dict(v.to_dict())

    return v


class SpecialTypesEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (set, frozenset, RequestResult, Future, JsonBuilder)):
            return _check_value(obj)
        return json.JSONEncoder.default(self, obj)


class JsonBuilder(object):
    __slots__ = ('_data', '_encoder', 'root_node_name')

    def __init__(self, root_node_name=None, json_encoder=None):
        self._data = []
        self._encoder = json_encoder
        self.root_node_name = root_node_name

    def put(self, *args, **kwargs):
        self._data.extend(args)
        if kwargs:
            self._data.append(kwargs)

    def is_empty(self):
        return len(self._data) == 0

    def clear(self):
        self._data = []

    @staticmethod
    def get_error_node(exception):
        return {
            'error': {k: v for k, v in exception.attrs.iteritems()}
        }

    def to_dict(self, _deep=True):
        result = {}
        for chunk in self._data:
            # _deep=False does not perform a full recursive walk, relying on JSONEncoder instead
            # this is an optimization used in `to_string` method
            if _deep or isinstance(chunk, (RequestResult, Future, JsonBuilder)):
                chunk = _check_value(chunk)

            if chunk is not None:
                result.update(chunk)

        if self.root_node_name is not None:
            result = {self.root_node_name: result}

        return result

    def to_string(self):
        result = self.to_dict(_deep=False)

        if self._encoder is not None:
            return json.dumps(result, cls=self._encoder, ensure_ascii=False)

        return json.dumps(result, cls=SpecialTypesEncoder, ensure_ascii=False)
