from lxml import etree

import frontik.handler
import frontik.jobs


class Page(frontik.handler.PageHandler):
    def get_page(self):

        end = self.finish_group.add(lambda: None)

        def job():
            self.get_argument('nofail')

        def success_cb(res):
            self.doc.put(etree.Element('ok'))
            end()

        def exception_cb(e):
            raise e

        frontik.jobs.get_threadpool_executor().add_job(
            job, self.check_finished(success_cb), self.check_finished(exception_cb)
        )
