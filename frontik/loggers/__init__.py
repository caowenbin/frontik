# coding=utf-8

from frontik.loggers import sentry

def bootstrap_all_loggers(application):
    for logger in (sentry,):
        logger.bootstrap_logger(application)
