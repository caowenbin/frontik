# coding=utf-8

from frontik.app import FrontikApplication

from tests.projects.re_app import config
from tests.projects.re_app.pages import handler_404


class TestApplication(FrontikApplication):
    def application_config(self):
        return config

    def application_urls(self):
        return config.urls

    def application_404_handler(self):
        return handler_404.Page
