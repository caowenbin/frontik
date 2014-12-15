#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This is module for creating of init.d scripts for tornado-based
services

It implements following commands:
* start
* stop
* restart
* status

Sample usage:

=== /etc/init.d/frontik ===
#!/usr/bin/python
# coding=utf-8

from tornado_util.supervisor import supervisor

supervisor(
    script='/usr/bin/frontik_srv.py',
    app='/usr/share/pyshared/application',
    config='/etc/frontik/frontik.cfg'
)

All exit codes returned by commands are trying to be compatible with LSB standard [1] as much as possible

[1] http://refspecs.linuxbase.org/LSB_3.1.1/LSB-Core-generic/LSB-Core-generic/iniscrptact.html

"""

import signal
import sys
import urllib2
import logging
import subprocess
import time
import glob
import re
import socket
import os
import resource

from daemon.daemon import close_all_open_files
from tornado.log import LogFormatter
import tornado.options
from tornado.options import options

from frontik import server
from frontik.launcher.common_worker import get_common_workers

tornado.options.define('workers_count', 4, int)
tornado.options.define('logfile_template', None, str)
tornado.options.define('pidfile_template', None, str)
tornado.options.define('supervisor_sigterm_timeout', 4, int)
tornado.options.define('nofile_soft_limit', 4096, int)


def is_alive(port, **kwargs):
    try:
        with open(options.pidfile_template % {'port': port}) as f:
            pid = f.read().strip()

        with open('/proc/{0}/cmdline'.format(pid), 'r') as cmdline_file:
            cmdline = cmdline_file.readline()
            if cmdline is not None and 'python' in cmdline:
                return True

        return False

    except (IOError, subprocess.CalledProcessError):
        return False


def is_running(port):
    try:
        response = urllib2.urlopen('http://localhost:{}/status/'.format(port), timeout=1)
        for header, value in response.info().items():
            if header == 'server' and value.startswith('TornadoServer'):
                return True

        return False
    except urllib2.URLError:
        return False
    except socket.error as e:
        logging.warn('socket error (%s) on port %s', e, port)
        return False


def start_worker(config=None, port=None, worker=None):
    if is_alive(port):
        logging.warn('another worker already started on %s', port)
        return

    logging.debug('start worker %s', port)

    first_pid = os.fork()
    if first_pid == 0:

        second_pid = os.fork()
        if second_pid == 0:

            close_all_open_files()

            pidfile_name = options.pidfile_template % {'port': port}
            with open(pidfile_name, 'w+') as pidfile:
                pidfile.write(str(os.getpid()))

            worker(config_file=config, port=port)

        sys.exit(0)


def stop_worker(port, signal_to_send=signal.SIGTERM):
    logging.debug('stop worker %s', port)
    pid_path = options.pidfile_template % {'port': port}

    if not os.path.exists(pid_path):
        logging.warning('pidfile %s does not exist, dont know how to stop', pid_path)

    try:
        with open(pid_path) as f:
            pid = int(f.read().strip())

        os.kill(pid, signal_to_send)
    except (OSError, IOError, ValueError):
        pass


def rm_pidfile(port):
    pid_path = options.pidfile_template % {'port': port}
    if os.path.exists(pid_path):
        try:
            os.remove(pid_path)
        except:
            logging.warning('failed to rm %s', pid_path)


def map_workers_by_port(f, **kwargs):
    return [f(port=options.port + p, **kwargs) for p in range(options.workers_count)]


def map_stale_workers(f, **kwargs):
    ports = [str(options.port + p) for p in range(options.workers_count)]
    stale_ports = []

    if '%(port)s' in options.pidfile_template:
        path_beginning, _, path_ending = options.pidfile_template.partition('%(port)s')
        re_escaped_template = ''.join([re.escape(path_beginning), '([0-9]+)', re.escape(path_ending)])

        # extract ports from pid file names and add them to stale_ports if they are not in ports from settings
        for pidfile in glob.glob(options.pidfile_template % {'port': '*'}):
            port_match = re.search(re_escaped_template, pidfile)
            if port_match and not port_match.group(1) in ports:
                stale_ports.append(port_match.group(1))

    return [f(port=p, **kwargs) for p in stale_ports]


def map_custom_workers(f, **kwargs):
    return [f(port=worker_name, worker=worker, **kwargs) for worker_name, worker in get_common_workers().items()]


def map_all_workers(f, **kwargs):
    return map_custom_workers(f, **kwargs) + map_workers_by_port(f, **kwargs) + map_stale_workers(f, **kwargs)


def stop():
    if any(map_all_workers(is_alive)):
        logging.warning('some of the workers are running; trying to kill')

    map_all_workers(lambda port, **kwargs: stop_worker(port, signal.SIGTERM) if is_alive(port) else rm_pidfile(port))
    time.sleep(int(options.supervisor_sigterm_timeout))

    map_all_workers(lambda port, **kwargs: stop_worker(port, signal.SIGKILL) if is_alive(port) else rm_pidfile(port))
    time.sleep(0.1 * options.workers_count)

    map_all_workers(
        lambda port, **kwargs: rm_pidfile(port) if not is_alive(port) else logging.warning('failed to stop worker on port %s', port)
    )

    if any(map_all_workers(is_alive)):
        logging.warning('failed to stop workers')
        sys.exit(1)


def _check_start_status(port, check_running=True, **kwargs):
    alive = is_alive(port)
    running = not check_running or is_running(port)

    if alive and running:
        return True

    if not alive and not running:
        logging.error('worker %s failed to start', port)
        return True

    logging.info('waiting for worker %s to start', port)
    return False


def start(config):
    map_custom_workers(start_worker, config=config)

    map_workers_by_port(start_worker, config=config, worker=server.main)

    time.sleep(1)
    while not all(map_custom_workers(_check_start_status, check_running=False) + map_workers_by_port(_check_start_status)):
        time.sleep(1)

    map_workers_by_port(lambda port: rm_pidfile(port) if not is_alive(port) else 0)


def status(expect=None):
    res = map_stale_workers(is_running)
    if any(res):
        logging.warn('some stale workers are running!')

    res = map_custom_workers(is_alive) + map_workers_by_port(is_running)

    if all(res):
        if expect == 'stopped':
            logging.error('all workers are running')
            return 1
        else:
            logging.info('all workers are running')
            return 0
    elif any(res):
        logging.warn('some workers are running!')
        return 1
    else:
        if expect == 'started':
            logging.error('all workers are stopped')
            return 1
        else:
            logging.info('all workers are stopped')
            return 3


def supervisor(script=None, config=None, app=None):
    tornado.options.parse_config_file(config, final=False)
    (cmd,) = tornado.options.parse_command_line(final=False)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.NOTSET)

    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(LogFormatter(
        fmt='%(color)s[%(asctime)s %(name)s]%(end_color)s %(message)s', datefmt='%H:%M:%S'
    ))

    root_logger.addHandler(handler)

    cur_soft_limit, cur_hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
    new_soft_limit = options.nofile_soft_limit
    try:
        resource.setrlimit(resource.RLIMIT_NOFILE, (new_soft_limit, max(new_soft_limit, cur_hard_limit)))
    except ValueError:
        logging.warning('We don\'t have CAP_SYS_RESOURCE, therefore soft NOFILE limit will be set to {0}'.format(
            min(new_soft_limit, cur_hard_limit)))
        resource.setrlimit(resource.RLIMIT_NOFILE, (min(new_soft_limit, cur_hard_limit), cur_hard_limit))

    if cmd == 'start':
        start(config)
        sys.exit(status(expect='started'))

    if cmd == 'restart':
        stop()
        start(config)
        sys.exit(status(expect='started'))

    elif cmd == 'stop':
        stop()
        status_code = status(expect='stopped')
        sys.exit(0 if status_code == 3 else 1)

    elif cmd == 'status':
        sys.exit(status())

    else:
        logging.error('either --start, --stop, --restart or --status should be present')
        sys.exit(1)
