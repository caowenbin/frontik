import random
import string

from lxml import etree

from frontik.handler import PageHandler


def random_word(length):
    return ''.join(random.choice(string.lowercase) for i in xrange(length))

DATA = []
for i in xrange(500):
    element = etree.Element(random_word(10))
    for k in xrange(5):
        subelement = etree.Element(random_word(15))
        subelement.text = random_word(20)
        element.append(subelement)
    DATA.append(element)


class Page(PageHandler):
    def get_page(self):
        for e in DATA:
            self.doc.put(e)

    def compute_etag(self):
        return None
