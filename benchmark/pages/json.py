import random
import string

from frontik.handler import PageHandler


def random_word(length):
    return ''.join(random.choice(string.lowercase + string.digits) for i in xrange(length))

DATA = [{random_word(10): {random_word(15): random_word(20)} for k in xrange(5)} for i in xrange(500)]


class Page(PageHandler):
    def get_page(self):
        for i in DATA:
            self.json.put(i)

    def compute_etag(self):
        return None
