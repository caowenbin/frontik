#!/usr/bin/python

import resource
import subprocess
import sys

from tornado_util import supervisor

from tests.instances import get_free_port, wait_for


def run_benchmark(profile=False):
    port = get_free_port()
    resource.setrlimit(resource.RLIMIT_NOFILE, (4096, 4096))

    command = './scripts/frontik'
    if profile:
        command = 'python -m cProfile -o benchmark.profile ' + command

    supervisor.start_worker(command, app='./benchmark', config='./benchmark/frontik.cfg', port=port)
    wait_for(lambda: supervisor.is_running(port))

    print '(1) json'
    subprocess.call('ab -c 35 -n 7000 -v 1 -q "http://localhost:{}/json" | fgrep "(mean)"'.format(port), shell=True)

    print '(2) xml'
    subprocess.call('ab -c 35 -n 7000 -v 1 -q "http://localhost:{}/xml" | fgrep "(mean)"'.format(port), shell=True)

    print '(3) preprocessors'
    subprocess.call('ab -c 35 -n 7000 -v 1 -q "http://localhost:{}/preprocessors" | fgrep "(mean)"'.format(port), shell=True)

    supervisor.stop_worker(port)
    wait_for(lambda: not supervisor.is_running(port))
    supervisor.rm_pidfile(port)

if __name__ == '__main__':
    profile = len(sys.argv) > 1 and sys.argv[1] == '--profile'
    run_benchmark(profile=profile)
