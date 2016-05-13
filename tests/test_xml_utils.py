# coding=utf-8

import unittest

from lxml import etree

from . import py3_skip
from frontik.testing.xml_asserts import XmlTestCaseMixin
from frontik.xml_util import xml_to_dict, dict_to_xml

xml = '''
    <root>
        <key1>value</key1>
        <key2></key2>
        <nested>
            <key1>русский текст</key1>
            <key2>русский текст</key2>
        </nested>
        <complexNested>
            <nested>
                <key>value</key>
                <otherKey>otherValue</otherKey>
            </nested>
            <other>123</other>
        </complexNested>
    </root>
    '''

dictionary_before = {
    'key1': 'value',
    'key2': '',
    'nested': {
        'key1': u'русский текст'.encode('utf-8'),
        'key2': u'русский текст'
    },
    'complexNested': {
        'nested': {
            'key': 'value',
            'otherKey': 'otherValue'
        },
        'other': 123
    }
}

dictionary_after = {
    'key1': 'value',
    'key2': '',
    'nested': {
        'key1': u'русский текст',
        'key2': u'русский текст'
    },
    'complexNested': {
        'nested': {
            'key': 'value',
            'otherKey': 'otherValue'
        },
        'other': '123'
    }
}


class TestXmlUtils(unittest.TestCase, XmlTestCaseMixin):
    @py3_skip
    def test_xml_to_dict_and_back_again(self):
        self.assertEqual(xml_to_dict(etree.XML(xml)), dictionary_after)
        self.assertXmlEqual(dict_to_xml(dictionary_before, 'root'), xml)
        self.assertEqual(xml_to_dict(dict_to_xml(dictionary_before, 'root')), dictionary_after)
