# coding=utf-8

import unittest

from lxml import etree
from lxml_asserts.testcase import LxmlTestCaseMixin
from tornado.concurrent import Future

from frontik.doc import Doc
from frontik.http_client import RequestResult, FailedRequestException


class TestDoc(unittest.TestCase, LxmlTestCaseMixin):
    def test_simple(self):
        d = Doc('a')

        self.assertTrue(d.is_empty())

        d.put(etree.Element(u'тест'))

        self.assertFalse(d.is_empty())
        self.assertXmlEqual(
            d.to_etree_element(),
            b"""<?xml version='1.0' encoding='utf-8'?>\n<a><\xd1\x82\xd0\xb5\xd1\x81\xd1\x82/></a>"""
        )

    def test_future_simple(self):
        d = Doc('a')
        f = Future()
        d.put(f)

        self.assertXmlEqual(d.to_etree_element(), b"""<?xml version='1.0' encoding='utf-8'?>\n<a/>""")

        f.set_result(etree.Element('b'))

        self.assertXmlEqual(d.to_etree_element(), b"""<?xml version='1.0' encoding='utf-8'?>\n<a><b/></a>""")

    def test_future_list(self):
        d = Doc('a')
        f = Future()
        f.set_result([etree.Comment('ccc'), etree.Element('bbb')])
        d.put(f)

        self.assertXmlEqual(d.to_etree_element(), u"""<?xml version='1.0'?>\n<a><!--ccc--><bbb/></a>""")

    def test_failed_future(self):
        d = Doc('a')
        f = Future()
        result = RequestResult()
        result.set_exception(FailedRequestException(reason='error', code='code'))
        f.set_result(result)
        d.put(f)

        self.assertXmlEqual(
            d.to_etree_element(), u"""<?xml version='1.0'?>\n<a><error reason="error" code="code"/></a>"""
        )

    def test_doc_nested(self):
        a = Doc('a')
        a.put(etree.fromstring('<b>test</b>'))

        self.assertXmlEqual(
            a.to_etree_element(), b"""<?xml version='1.0' encoding='utf-8'?>\n<a><b>test</b></a>"""
        )

    def test_unsupported_types(self):
        a = Doc('a').put('1')
        b = Doc('b').put(1)

        self.assertRaises(ValueError, a.to_etree_element)
        self.assertRaises(ValueError, b.to_etree_element)

    def test_serializable(self):
        class Serializable(object):
            def __init__(self, tag, value):
                self.tag = tag
                self.value = value

            def to_etree_element(self):
                result = etree.Element(self.tag)
                result.text = self.value
                return result

        a = Doc('a')
        a.put(Serializable('testNode', 'vally'))

        self.assertEqual(
            a.to_string(), b"""<?xml version='1.0' encoding='utf-8'?>\n<a><testNode>vally</testNode></a>"""
        )

    def test_root_node(self):
        d = Doc(root_node=etree.Element('doc'))
        d.put(etree.Element('test1'))

        self.assertXmlEqual(
            d.to_etree_element(), b"""<?xml version='1.0' encoding='utf-8'?>\n<doc><test1/></doc>"""
        )

    def test_root_node_doc(self):
        d1 = Doc('a')
        d1.put(etree.Comment('1'))

        d2 = Doc(root_node=d1)
        d2.put(etree.Comment('2'))

        self.assertXmlEqual(
            d2.to_etree_element(), b"""<?xml version='1.0' encoding='utf-8'?>\n<a><!--1--><!--2--></a>"""
        )

    def test_string_as_root_node(self):
        d = Doc(root_node='a')
        self.assertXmlEqual(d.to_etree_element(), b"""<?xml version='1.0' encoding='utf-8'?>\n<a></a>""")

    def test_root_node_invalid(self):
        self.assertRaises(TypeError, Doc, root_node=etree.Comment('invalid root doc'))
