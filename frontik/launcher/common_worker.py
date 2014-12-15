# coding=utf-8

import time
import zlib

from lxml import etree

import tornado.ioloop
import tornado.web
from tornado.escape import utf8

parser = etree.XMLParser()
_xml_parser = etree.XMLParser(strip_cdata=False)


class MainHandler(tornado.web.RequestHandler):
    def post(self):
        try:
            xml_string = self.get_argument('xml')
            xsl_name = self.get_argument('xsl')

            with open('/home/andrew/work/frontik/asdf', 'a+', buffering=0) as f:
                f.write(xml_string[:100] + '-' + xsl_name + '\n')

            start_time = time.time()
            transform = etree.XSLT(etree.parse(xsl_name, parser))
            self.write(str(transform(etree.fromstring(utf8(xml_string), parser=_xml_parser))))

            with open('/home/andrew/work/frontik/asdf', 'a+', buffering=0) as f:
                f.write(str(time.time() - start_time) + '\n')

        except Exception as e:
            with open('/home/andrew/work/frontik/asdf', 'a+', buffering=0) as f:
                f.write(str(e) + '\n')


class XsltWorker(object):
    def __init__(self):
        self.port = 9600

    def __call__(self, config_file=None, port=None):
        import zmq
        from zmq.eventloop import ioloop, zmqstream
        loop = ioloop.IOLoop.instance()

        ctx = zmq.Context()
        s = ctx.socket(zmq.REP)
        s.bind('tcp://127.0.0.1:5555')

        stream = zmqstream.ZMQStream(s, loop)

        def echo(msg):
            try:
                # data = cPickle.loads(msg[0])
                data = zlib.decompress(msg[0])

                start_time = time.time()
                transform = etree.XSLT(etree.parse(data['xsl'], parser))
                result = str(transform(etree.fromstring(utf8(data['xml']), parser=_xml_parser)))

                with open('/home/andrew/work/frontik/asdf', 'a+', buffering=0) as f:
                    f.write(str(time.time() - start_time) + '\n')

                stream.send(result)

            except Exception as e:
                with open('/home/andrew/work/frontik/asdf', 'a+', buffering=0) as f:
                    f.write(str(e) + '\n')

        stream.on_recv(echo)
        loop.start()


_common_workers = {
    'xslt': XsltWorker()
}


def get_common_workers():
    return _common_workers
