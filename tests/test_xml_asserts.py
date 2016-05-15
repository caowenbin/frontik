# coding=utf-8

import unittest

from lxml import etree

from frontik.compat import unicode_type
from frontik.testing import xml_asserts


class TestXmlResponseMixin(unittest.TestCase, xml_asserts.XmlTestCaseMixin):
    def test_assertXmlEqual_fail_custom_message(self):
        with self.assertRaises(AssertionError) as e:
            self.assertXmlEqual('<a/>', '<b/>', msg='Custom message')

        self.assertEqual(unicode_type(e.exception), u'Custom message — Tags do not match: /a != /b')

    def test_assertXmlEqual_different_tag_names(self):
        with self.assertRaises(AssertionError) as e:
            self.assertXmlEqual('<a/>', '<b/>')

        self.assertEqual(unicode_type(e.exception), u'XML documents are not equal — Tags do not match: /a != /b')

    def test_assertXmlEqual_missing_attributes(self):
        with self.assertRaises(AssertionError) as e:
            self.assertXmlEqual('<a x="1" y="2"/>', '<a y="2"/>')

        self.assertEqual(
            unicode_type(e.exception), u'XML documents are not equal — Second xml misses attributes: /a/(x)'
        )

    def test_assertXmlEqual_added_attributes(self):
        with self.assertRaises(AssertionError) as e:
            self.assertXmlEqual('<a y="2"/>', '<a x="1" y="2"/>')

        self.assertEqual(
            unicode_type(e.exception),
            u'XML documents are not equal — Second xml has additional attributes: /a/(x)'
        )

    def test_assertXmlEqual_different_attribute_values(self):
        with self.assertRaises(AssertionError) as e:
            self.assertXmlEqual('<a x="1" y="2"/>', '<a x="абв" y="2"/>')

        self.assertEqual(
            unicode_type(e.exception),
            u"XML documents are not equal — Attribute values are not equal: /a/x['1' != 'абв']"
        )

    def test_assertXmlEqual_different_tag_text(self):
        with self.assertRaises(AssertionError) as e:
            self.assertXmlEqual('<a>123</a>', '<a>абв</a>')

        self.assertEqual(
            unicode_type(e.exception), u"XML documents are not equal — Tags text differs: /a['123' != 'абв']"
        )

    def test_assertXmlEqual_different_child_tag_tail(self):
        with self.assertRaises(AssertionError) as e:
            self.assertXmlEqual('<a><b/>123</a>', '<a><b/>абв</a>')

        self.assertEqual(
            unicode_type(e.exception), u"XML documents are not equal — No equal child found in second xml: /a/b"
        )

    def test_assertXmlEqual_different_children(self):
        with self.assertRaises(AssertionError) as e:
            self.assertXmlEqual('<a><b/><c/></a>', '<a><b/></a>')

        self.assertEqual(
            unicode_type(e.exception),
            u'XML documents are not equal — Children are not equal: /a[2 children != 1 children]'
        )

    def test_assertXmlEqual_different_children_order(self):
        self.assertXmlEqual('<a><b/><c/></a>', '<a><c/><b/></a>')

    def test_assertXmlEqual_different_children_order_fail(self):
        with self.assertRaises(AssertionError) as e:
            self.assertXmlEqual('<a><b/><c/></a>', '<a><c/><b/></a>', check_tags_order=True)

        self.assertEqual(
            unicode_type(e.exception), u'XML documents are not equal — Tags do not match: /a/b != /a/c'
        )

    TREE = '''
        <elem start="17" end="18">
            <zAtrib/>
            <aAtrib>
                <cAtrib/>
                <bAtrib a="1" b="2"/>
            </aAtrib>
        </elem>
        '''.strip()

    def test_assertXmlEqual_absolute_equal(self):
        self.assertXmlEqual(self.TREE, self.TREE)
        self.assertXmlEqual(etree.fromstring(self.TREE), self.TREE)

    def test_assertXmlEqual(self):
        tree1 = '''
            <elem>
                <a/>
                <a>
                    <c prop="1">
                        <d prop="x"/>
                        <d prop="y"/>
                        <d/>
                    </c>
                    <c prop="1" a="1"/>
                    <c/>
                </a>
            </elem>
            '''.strip()

        tree2 = '''
            <elem>
                <a>
                    <c/>
                    <c prop="1" a="1"/>
                    <c prop="1">
                        <d prop="x"/>
                        <d/>
                        <d prop="y"/>
                    </c>
                </a>
                <a/>
            </elem>
            '''.strip()

        self.assertXmlEqual(tree1, tree2)
        self.assertXmlEqual(etree.fromstring(tree1), tree2)

    def test_assertXmlEqual_comments(self):
        self.assertXmlEqual(
            b'<?xml version="1.0" encoding="utf-8"?><root><!--a--><!--b--><!--\xd0\xb0\xd0\xb1\xd0\xb2--></root>',
            b'<?xml version="1.0" encoding="utf-8"?><root><!--\xd0\xb0\xd0\xb1\xd0\xb2--><!--b--><!--a--></root>'
        )

    def test_assertXmlCompatible_absolute_equals(self):
        self.assertXmlCompatible(self.TREE, self.TREE)

    def test_assertXmlCompatible_fail_custom_message(self):
        with self.assertRaises(AssertionError) as e:
            self.assertXmlCompatible('<a/>', '<b/>', msg='Custom message')

        self.assertEqual(unicode_type(e.exception), u'Custom message — Tags do not match: /a != /b')

    def test_assertXmlCompatible_added_attributes(self):
        tree1 = '''
            <elem>
                <a answer="42" douglas="adams"/>
            </elem>
            '''.strip()

        tree2 = '''
            <elem prop="some">
                <a answer="42" new2="no" douglas="adams" new="yes"/>
            </elem>
            '''.strip()

        self.assertXmlCompatible(tree1, tree2)

    def test_assertXmlCompatible_no_tags_in_first_xml(self):
        self.assertXmlCompatible('<a/>', '<a><x/><y/></a>')

    def test_assertXmlCompatible_extra_tags(self):
        tree1 = '''
            <elem>
                <z prop="1"/>
                <a>
                    <c/>
                    <c month="jan"/>
                    <b/>
                </a>
                <z prop="3"/>
                <a disabled="true"/>
                <txt>some text</txt>
            </elem>
            '''.strip()

        tree2 = '''
            <elem>
                <a disabled="true"/>
                <a>
                    <aa/>
                    <b/>
                    <c month="apr"/>
                    <c month="jan"/>
                    <c/>
                    <dd/>
                </a>
                <txt>some text</txt>
                <txt>some new text</txt>
                <z prop="3"/>
                <z prop="1">
                    <new nested="tag"/>
                </z>
                <yy/>
            </elem>
            '''.strip()

        self.assertXmlCompatible(tree1, tree2)

    def test_assertXmlCompatible_missing_children(self):
        with self.assertRaises(AssertionError) as e:
            self.assertXmlCompatible('<a><b/><c/></a>', '<a><b/></a>')

        self.assertEqual(
            unicode_type(e.exception),
            u'XML documents are not compatible — Second xml /a contains less children (1 < 2)'
        )

    def test_assertXmlCompatible_different_children(self):
        with self.assertRaises(AssertionError) as e:
            self.assertXmlCompatible('<a><b/><c/></a>', '<a><d/><b/></a>')

        self.assertEqual(
            unicode_type(e.exception),
            u'XML documents are not compatible — Second xml has no compatible child for /a/c'
        )

    def test_assertXmlCompatible_missing_children_recursive(self):
        with self.assertRaises(AssertionError) as e:
            self.assertXmlCompatible('<a><b><c/><d/></b></a>', '<a><b><c/></b></a>')

        self.assertEqual(
            unicode_type(e.exception),
            u'XML documents are not compatible — Second xml has no compatible child for /a/b'
        )

    def test_assertXmlCompatible_incompatible_attributes(self):
        tree1 = '''
            <elem>
                <a answer="42" douglas="adams"/>
            </elem>
            '''.strip()

        tree2 = '''
            <elem>
                <a douglas="adams" extra="extra"/>
            </elem>
            '''.strip()

        with self.assertRaises(AssertionError) as e:
            self.assertXmlCompatible(tree1, tree2)

        self.assertEqual(
            unicode_type(e.exception),
            u'XML documents are not compatible — Second xml has no compatible child for /elem/a'
        )

    def test_assertXmlCompatible_not_enough_compatible(self):
        tree1 = '''
           <root>
               <a x="1"/>
               <a y="1"/>
               <a z="1"><c/></a>
           </root>
        '''

        tree2 = '''
           <root>
               <a x="1" z="1"><b/></a>
               <a y="1"/>
               <a z="1"><b/></a>
           </root>
        '''

        with self.assertRaises(AssertionError) as e:
            self.assertXmlCompatible(tree1, tree2)

        self.assertIn(
            u'XML documents are not compatible — Second xml has no compatible child for /root/a',
            unicode_type(e.exception)
        )

    def test_assertXmlEqual_with_similar_children(self):
        xml_string = ('<a><b><c><d>1</d><e>2</e></c><f><g>3</g></f></b><h>4</h><i><l>5</l><m>6</m></i>'
                      '<i><l>7</l><m>8</m></i></a>')
        self.assertXmlEqual(xml_string, etree.fromstring(xml_string))
