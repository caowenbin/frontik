# coding=utf-8

from lxml import etree

from frontik.handler import HTTPErrorWithContent, PageHandler


class Page(PageHandler):
    def get_page(self):
        mode = self.get_argument('mode')

        if mode in ('xml', 'xslt'):
            self.doc.put(etree.fromstring('<ok xml="true"/>'))
        elif mode in ('json', 'jinja'):
            self.json.put({'content': 'json'})
        elif mode == 'text':
            self.text = 'Text content'

        if mode == 'xslt':
            self.set_xsl('simple.xsl')
        elif mode == 'jinja':
            self.set_template('postprocess.html')

        self.set_header('X-Custom-Header', 'value')

        raise HTTPErrorWithContent(int(self.get_argument('code', '200')), reason=self.get_argument('reason', None))
