# coding=utf-8

import unittest

from .instances import frontik_test_app


class TestPreprocessors(unittest.TestCase):
    def test_preprocessors(self):
        response_json = frontik_test_app.get_page_json('preprocessors')
        self.assertEqual(
            response_json,
            {
                'run': [
                    'pp0', 'pp1-before-yield', 'pp1-between-yield', 'pp1-after-yield', 'pp2', 'pp3', 'get_page'
                ],
                'post': ['pp0'],
                'postprocessor': True
            }
        )

    def test_preprocessors_finish_with_postprocessors(self):
        response_json = frontik_test_app.get_page_json('preprocessors?finish_with_postprocessors=true')
        self.assertEqual(
            response_json,
            {
                'run': ['pp0', 'pp1-before-yield', 'pp1-between-yield', 'pp1-after-yield', 'pp2'],
                'postprocessor': True
            }
        )

    def test_preprocessors_raise_error(self):
        response = frontik_test_app.get_page('preprocessors?raise_error=true')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, b'<html><title>400: Bad Request</title><body>400: Bad Request</body></html>')

    def test_preprocessors_finish(self):
        response = frontik_test_app.get_page_text('preprocessors?finish=true')
        self.assertEqual(response, 'finished')

    def test_preprocessors_redirect(self):
        response = frontik_test_app.get_page('preprocessors?redirect=true', allow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('redirected', response.headers.get('Location'))
