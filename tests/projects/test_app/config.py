# coding=utf-8


def post(self, data, cb):
    self.log.debug('posprocessor called')
    cb(data)

postprocessor = post

from lxml import etree
version = [etree.Element('app-version', number='last version')]
