# coding=utf-8

import unittest

from tornado.util import unicode_type

from frontik.argument_parser import Arg
from .instances import frontik_test_app


class TestArgumentParser(unittest.TestCase):
    def test_simple_types(self):
        self.assertEqual(Arg(str).parse('str_type', ['str_value']), 'str_value')
        self.assertEqual(Arg(int).parse('int_type', ['100']), 100)
        self.assertEqual(Arg(float).parse('float_type', ['0.5']), 0.5)

        self.assertTrue(Arg(bool).parse('bool_type', ['TruE']))
        self.assertFalse(Arg(bool).parse('bool_type', ['no']))

    def test_list_type(self):
        self.assertEqual(Arg([str]).parse('str_list_type', []), [])
        self.assertEqual(Arg([str]).parse('str_list_type', ['t1', 't2']), ['t1', 't2'])
        self.assertEqual(Arg([bool]).parse('bool_list_type', ['false']), [False])
        self.assertEqual(Arg([int]).parse('int_list_type', ['1']), [1])
        self.assertEqual(Arg([float]).parse('float_list_type', ['1.0', '2.0', '3.0']), [1.0, 2.0, 3.0])

    def test_default(self):
        self.assertEqual(Arg(str, default='default').parse('str_type', []), 'default')
        self.assertEqual(Arg([str], default=None).parse('str_list_type', []), None)

    def test_invalid_values(self):
        with self.assertRaises(ValueError) as e:
            Arg(int).parse('int_type', ['100r'])

        self.assertIn(u'parameter "int_type" must be of type int, got "100r"', unicode_type(e.exception))

        with self.assertRaises(ValueError) as e:
            Arg(float).parse('float_type', ['test'])

        self.assertIn(u'parameter "float_type" must be of type float, got "test"', unicode_type(e.exception))

        with self.assertRaises(ValueError) as e:
            Arg([int]).parse('int_list_type', ['1', '2', 'r'])

        self.assertIn(u'parameter "int_list_type" must be of type [int], got [1, 2, r]', unicode_type(e.exception))

    def test_default_on_error(self):
        self.assertEqual(Arg(int, default=100, default_on_error=True).parse('int_type', 'test'), 100)
        self.assertEqual(Arg([float], default=1, default_on_error=True).parse('float_type', 'test'), 1)

        with self.assertRaises(AssertionError) as e:
            Arg(int, default_on_error=True)

        self.assertIn(u'default_on_error = True, but no default value', unicode_type(e.exception))

    def test_empty_list_type(self):
        with self.assertRaises(AssertionError) as e:
            Arg([])

        self.assertIn('list argument must specify the type of its items', unicode_type(e.exception))

    def test_choice_type(self):
        self.assertEqual(Arg(str, choice=('t1', 't2', 't3')).parse('choice', ['t1']), 't1')

        self.assertEqual(
            Arg(str, choice=('t1', 't2', 't3'), default='tx', default_on_error=True).parse('choice', ['t4']), 'tx'
        )

        with self.assertRaises(ValueError) as e:
            Arg(str, choice=('t1', 't2')).parse('choice', ['t4'])

        self.assertIn(u'parameter "choice" must be one of the following: [t1, t2], got [t4]', unicode_type(e.exception))


class TestHandlerParseArguments(unittest.TestCase):
    def test_valid_types(self):
        result = frontik_test_app.get_page_json(
            'parse_arguments?str=str_value&int=100&bool=true&float=0.5&required=&list_str=a&list_str=b'
        )

        self.assertEqual(result['str'], 'str_value')
        self.assertEqual(result['str_alias'], 'str_value')
        self.assertEqual(result['int'], 100)
        self.assertEqual(result['float'], 0.5)
        self.assertEqual(result['bool'], True)
        self.assertEqual(result['list_str'], ['a', 'b'])

    def test_defaults(self):
        result = frontik_test_app.get_page_json('parse_arguments?required=')

        self.assertEqual(result['bool'], False)
        self.assertEqual(result['str'], 'str_default')
        self.assertEqual(result['int'], 123456)
        self.assertEqual(result['float'], 1.2)
        self.assertEqual(result['list_str'], ['list_default'])
        self.assertEqual(result['choice'], None)

    def test_missing_argument(self):
        response = frontik_test_app.get_page('parse_arguments')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, '{"error": "parameter \\"required\\" is missing"}')

    def test_invalid_argument(self):
        response = frontik_test_app.get_page('parse_arguments?int=test&required=')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.content, '{"error": "parameter \\"int\\" must be of type int, got \\"test\\""}'
        )

    def test_invalid_list(self):
        response = frontik_test_app.get_page('parse_arguments?list_int=1&list_int=test&required=')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.content, '{"error": "parameter \\"list_int\\" must be of type [int], got [1, test]"}'
        )

    def test_invalid_choice(self):
        response = frontik_test_app.get_page('parse_arguments?choice=t4&required=')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.content, '{"error": "parameter \\"choice\\" must be one of the following: [t1, t2, t3], got [t4]"}'
        )
