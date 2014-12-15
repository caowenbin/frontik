# coding=utf-8

from functools import partial
import Queue
import threading
import time
import logging
import zlib

import tornado.options
from tornado import stack_context
from tornado.ioloop import IOLoop

jobs_log = logging.getLogger('frontik.jobs')
__threadpool_executor = None


def queue_worker(queue):
    while True:
        try:
            (prio, (func, cb, exception_cb)) = queue.get(timeout=10)
        except Queue.Empty:
            if tornado.options.options.warn_no_jobs:
                jobs_log.warning('no job in 10 secs')
            continue
        except Exception:
            jobs_log.exception('cannot get new job')
            continue

        try:
            IOLoop.instance().add_callback(partial(cb, func()))
        except Exception as e:
            jobs_log.exception('cannot perform job')
            IOLoop.instance().add_callback(partial(exception_cb, e))


class IOLoopExecutor(object):
    @staticmethod
    def add_job(func, cb, exception_cb, prio=None):
        def _wrapper():
            try:
                cb(func())
            except Exception as e:
                exception_cb(e)

        IOLoop.instance().add_callback(_wrapper)


class ThreadPoolExecutor(object):
    count = 0

    def __init__(self, pool_size):
        assert pool_size > 0
        self.events = Queue.PriorityQueue()

        jobs_log.debug('pool size: ' + str(pool_size))
        self.workers = [threading.Thread(target=partial(queue_worker, self.events)) for i in range(pool_size)]
        [i.setDaemon(True) for i in self.workers]
        [i.start() for i in self.workers]
        jobs_log.debug('active threads count = ' + str(threading.active_count()))

    def add_job(self, func, cb, exception_cb, prio=10):
        try:
            ThreadPoolExecutor.count += 1
            self.events.put((
                (prio, ThreadPoolExecutor.count),
                (func, stack_context.wrap(cb), stack_context.wrap(exception_cb))
            ))
        except Exception as e:
            jobs_log.exception('cannot put job to queue')
            IOLoop.instance().add_callback(partial(exception_cb, e))


class HttpExecutor(object):
    @staticmethod
    def add_job(fetcher, data, cb, exception_cb):
        import zmq
        from zmq.eventloop import ioloop, zmqstream

        def _cb(msg):

            reply = msg[0]
            stream.close()

            if reply:
                cb(((time.time() - start_time) * 1000, reply, None))

            # if data is None or response.error:
            #     exception_cb(ValueError())
            # else:
            #     cb(((time.time() - start_time) * 1000, data, None))

        start_time = time.time()

        ctx = zmq.Context.instance()
        s = ctx.socket(zmq.REQ)
        s.connect('tcp://127.0.0.1:5555')

        stream = zmqstream.ZMQStream(s)
        stream.on_recv(_cb)

        # send request to worker
        # s.send(cPickle.dumps(data))
        s.send(zlib.compress(data))


def get_threadpool_executor():
    global __threadpool_executor
    if __threadpool_executor is None:
        __threadpool_executor = ThreadPoolExecutor(tornado.options.options.executor_pool_size)
    return __threadpool_executor


def get_executor(executor_type):
    if executor_type == 'threaded':
        return get_threadpool_executor()
    elif executor_type == 'ioloop':
        return IOLoopExecutor
    elif executor_type == 'http':
        return HttpExecutor
    else:
        raise ValueError('Invalid value for executor_type: "{0}"'.format(executor_type))
