import frontik.handler

from frontik.launcher.common_worker import get_common_workers


class Page(frontik.handler.PageHandler):
    def get_page(self):
        worker = get_common_workers()['xslt']
        worker.send_message('HIIII')
