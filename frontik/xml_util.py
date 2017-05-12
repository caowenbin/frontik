# coding=utf-8

from lxml import etree

from frontik.util import any_to_unicode


def dict_to_xml(dict_value, element_name):
    element = etree.Element(element_name)
    if not isinstance(dict_value, dict):
        element.text = any_to_unicode(dict_value)
        return element

    for k, v in dict_value.items():
        element.append(dict_to_xml(v, k))
    return element


def xml_to_dict(xml):
    if len(xml) == 0:
        return xml.text if xml.text is not None else ''

    return {e.tag: xml_to_dict(e) for e in xml}
