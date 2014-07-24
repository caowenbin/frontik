# coding=utf-8

import frontik.handler


class Page(frontik.handler.PageHandler):
    def get_page(self):
        self.parse_argument('required', str)

        args_spec = {
            'bool': Page.Arg(bool, default=False),
            'str': Page.Arg(str, default='str_default'),
            'str_alias': Page.Arg(str, name='str', default='str_default'),
            'int': Page.Arg(int, default=123456),
            'float': Page.Arg(float, default=1.2, default_on_error=True),
            'list_str': Page.Arg([str], default=['list_default']),
            'list_int': Page.Arg([int]),
            'choice': Page.Arg(str, choice=('t1', 't2', 't3'), default=None)
        }

        self.json.put(self.parse_arguments(args_spec))

    def write_error(self, status_code=500, **kwargs):
        if 'exc_info' in kwargs:
            exception = kwargs['exc_info'][1]
        else:
            exception = None

        if exception is not None:
            self.json.put({'error': exception.log_message})
            self.finish_with_postprocessors()
        else:
            super(Page, self).write_error(status_code, **kwargs)
