# coding=utf-8

import os

from frontik.app import FileMappingDispatcher

from . import pages
from .pages import exception_on_prepare, handler_404, httperror_on_prepare, id_param, simple

XML_root = None
XSL_root = os.path.normpath(os.path.join(os.path.dirname(__file__), 'xsl'))
XSL_cache_limit = 1

urls = [
    ('/id/(?P<id>[^/]+)', pages.id_param.Page),
    ('/not_simple', pages.simple.Page),
    ('/exception_on_prepare_rewrite', pages.exception_on_prepare.Page),
    ('/httperror_on_prepare_rewrite', pages.httperror_on_prepare.Page),
    ('(?!/not_matching_regex)', FileMappingDispatcher(pages, handler_404=pages.handler_404.Page))
]
