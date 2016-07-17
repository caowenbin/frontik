# coding=utf-8

import frontik.micro_handler
from frontik.handler import HTTPError


class Page(frontik.micro_handler.MicroHandler):
    def get_page(self):
        return {
            'xml': self.POST(self.request.host, self.request.path + '?mode=xml', fail_on_error=True),
            'json': self.POST(self.request.host, self.request.path + '?mode=json', fail_on_error=True),
        }

    @staticmethod
    def get_page_requests_failed(name, data, response):
        raise HTTPError(400)

    def post_page(self):
        mode = self.get_argument('mode')
        self.set_header('Content-Type', mode)

        if mode == 'xml':
            self.text = '''<doc frontik="tr"ue">this is broken xml</doc>'''
        elif mode == 'json':
            self.text = '''{"hel"lo" : "this is broken json"}'''
