#coding: utf-8

import imp
import logging
import sys
import re
import time

from request_context import in_context, get_to_dispatch, stats
import tornado.autoreload
import tornado.web
import tornado.ioloop
from tornado.options import options

import frontik.magic_imp
import frontik.doc
import frontik.handler_xml
import frontik.jobs
import tornado.curl_httpclient

from frontik import etree

log = logging.getLogger('frontik.server')

class VersionHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header('Content-Type', 'text/xml')
        versions = etree.Element("versions")

        from version import version
        etree.SubElement(versions, "frontik").text = version

        import frontik.options
        application_versions = etree.Element("applications")

        for path, app in options.urls:
            app_info = etree.Element("application", name=repr(app), path = path)
            try:
                application = app.ph_globals.config.version
                app_info.extend(list(application))
            except:
                etree.SubElement(app_info, "version").text = "app doesn't support version"
            etree.SubElement(app_info, "initialized_wo_error").text = str(app.initialized_wo_error)
            application_versions.append(app_info)
            
        versions.append(application_versions)
        self.write(frontik.doc.etree_to_xml(versions))


class StatusHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header('Content-Type', 'text/plain; charset=UTF-8')
        self.write('pages served: %s\n' % (stats.page_count,))
        self.write('http reqs made: %s\n' % (stats.http_reqs_count,))
        self.write('http reqs got: %s bytes\n' % (stats.http_reqs_size_sum,))
        cur_uptime = time.time() - stats.start_time
        if cur_uptime < 60:
            res = 'uptime for : %d seconds\n' % ((cur_uptime),)
        elif cur_uptime < 3600:
            res = 'uptime for : %d minutes\n' % ((cur_uptime/60),)
        else:
            res = 'uptime for : %d hours and %d minutes \n' % ((cur_uptime/3600), (cur_uptime % 3600)/60)

        self.write(res)


class StopHandler(tornado.web.RequestHandler):
    def get(self):
        log.info('requested shutdown')
        tornado.ioloop.IOLoop.instance().stop()


class PdbHandler(tornado.web.RequestHandler):
    def get(self):
        import pdb
        pdb.set_trace()


class CountPageHandlerInstancesHandler(tornado.web.RequestHandler):
    def get(self):
        import gc
        import frontik.handler
        hh = tuple([i for i in gc.get_objects()
                    if isinstance(i, frontik.handler.PageHandler)])

        #if len(hh) > 0:
        #    import pdb; pdb.set_trace()

        self.finish('{0}\n{1}'.format(len(hh), [i for i in gc.get_referrers(*hh)
                                                if i is not hh]))

class CountTypesHandler(tornado.web.RequestHandler):
    def get(self):
        import gc
        from collections import defaultdict

        counts = defaultdict(int)

        for o in gc.get_objects():
            counts[type(o)] += 1

        for k, v in sorted(counts.items(), key=lambda x:x[0]):
            self.write('%s\t%s\n' % (v, k))

        self.finish()


class Map2ModuleName(object):
    def __init__(self, module):
        self.module = module
        self.name = module.__name__
        self.log = logging.getLogger('frontik.map2pages.{0}'.format(self.name))
        self.log.info('initializing...')

    @in_context
    def __call__(self, application, request, context=None, **kwargs):
        context.log.info('requested url: %s (%s)', get_to_dispatch(request, 'uri'), request.uri)

        page_module_name = 'pages.' + '.'.join(get_to_dispatch(request,'path').strip('/').split('/'))
        context.log.debug('page module: %s', page_module_name)

        try:
            page_module = self.module.frontik_import(page_module_name)
            context.log.debug('using %s from %s', (self.name, page_module_name), page_module.__file__)
        except ImportError:
            context.log.exception('%s module not found', (self.name, page_module_name))
            return tornado.web.ErrorHandler(application, request, status_code=404)
        except AttributeError:
            context.log.exception('%s is not frontik application module, but needs to be and have "frontik_import" method', self.name)
            return tornado.web.ErrorHandler(application, request, status_code=500)
        except:
            context.log.exception('error while importing %s module', (self.name, page_module_name))
            return tornado.web.ErrorHandler(application, request, status_code=500)

        if not hasattr(page_module, 'Page'):
            context.exception('%s. Page class not found', page_module_name)
            return tornado.web.ErrorHandler(application, request, status_code=404)

        return page_module.Page(application, request, **kwargs)


class PageHandlerGlobals(object):
    '''
    Объект с настройками для всех хендлеров
    '''
    def __init__(self, app_package):
        self.config = app_package.config

        self.xml = frontik.handler_xml.PageHandlerXMLGlobals(app_package.config)

        self.http_client = tornado.curl_httpclient.CurlAsyncHTTPClient(max_clients = 200, max_simultaneous_connections = 200)

        self.executor = frontik.jobs.executor()


class App(object):
    def __init__(self, name, root):
        self.log = logging.getLogger('frontik.application.{0}'.format(name))
        self.name = name
        self.initialized_wo_error = True

        self.log.info('initializing...')
        try:
            self.importer = frontik.magic_imp.FrontikAppImporter(name, root)

            self.init_app_package(name)

            #Track all possible filenames for each app's config
            #module to reload in case of change
            for filename in self.importer.get_probable_module_filenames('config'):
                tornado.autoreload.watch_file(filename)

            self.ph_globals = PageHandlerGlobals(self.module)
        except Exception as e:
            #we do not want to break frontik on app
            #initialization error, so we report error and skip
            #the app.
            self.log.exception('failed to initialize, skipping from configuration')
            self._init_exception = e
            self.initialized_wo_error = False

    def init_app_package(self, name):
        self.module = imp.new_module(frontik.magic_imp.gen_module_name(name))
        sys.modules[self.module.__name__] = self.module

        self.pages_module = self.importer.imp_app_module('pages')
        sys.modules[self.pages_module.__name__] = self.pages_module

        try:
            self.module.config = self.importer.imp_app_module('config')
        except Exception, e:
            self.log.error('failed to load config: %s', e)
            raise

        if not hasattr(self.module.config, 'urls'):
            self.module.config.urls = [("", Map2ModuleName(self.pages_module)),]
        self.module.dispatcher = RegexpDispatcher(self.module.config.urls, self.module.__name__)

    @in_context
    def __call__(self, application, request, context = None, **kwargs):
        context.log.info('requested url: %s (%s)', get_to_dispatch(request, 'uri'), request.uri)
        if not self.initialized_wo_error:
            context.log.error('application not loaded, because of fail during initialization')
            context.log.error(self._init_exception)
            return tornado.web.ErrorHandler(application, request, status_code=404)
        return self.module.dispatcher(application, request, ph_globals = self.ph_globals, **kwargs)


class RegexpDispatcher(object):
    def __init__(self, app_list, name='RegexpDispatcher'):
        self.name = name
        log.info('initializing %r' % self)

        def parse_conf(pattern, app, parse=lambda x: [x,]):
            return re.compile(pattern), app, parse

        self.apps = map(lambda app_conf: parse_conf(*app_conf), app_list)
        log.info('finished initializing %r' % self)

    def __repr__(self):
        return "<RegexpDispatcher %s>" % self.name

    @in_context
    def __call__(self, application, request, context=None, **kwargs):
        context.log.debug('in %r' % self)
        for pattern, app, parse in self.apps:

            match = context.dispatch_on_url(pattern, parse)
            #app found
            if match:
                try:
                    return app(application, request, **kwargs)
                except tornado.web.HTTPError, e:
                    context.log.error('%s. Tornado error, %s', app, e)
                    return tornado.web.ErrorHandler(application, request, e.status_code)
                except Exception, e:
                    context.log.exception('%s. Internal server error, %s', app, e)
                return tornado.web.ErrorHandler(application, request, status_code=500)

        context.log.error('match for request url "%s" not found', request.uri)
        return tornado.web.ErrorHandler(application, request, status_code=404)

def get_app(app_urls, app_dict=None):
    app_roots = []
    if app_dict is not None:
        app_roots.extend([('/'+prefix.lstrip('/'), App(prefix.strip('/'), path)) for prefix, path in app_dict.iteritems()])
    app_roots.extend(app_urls)
    dispatcher = RegexpDispatcher(app_roots, 'root')

    return tornado.web.Application([
        (r'/version/', VersionHandler),
        (r'/status/', StatusHandler),
        (r'/stop/', StopHandler),
        (r'/types_count/', CountTypesHandler),
        (r'/pdb/', PdbHandler),
        (r'/ph_count/', CountPageHandlerInstancesHandler),
        (r'/.*', dispatcher),
        ])
