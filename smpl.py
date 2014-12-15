from frontik.launcher.supervisor import supervisor

supervisor(
    script='/usr/bin/frontik',  # ignored
    app='/usr/share/pyshared/xhh',  # ignored
    config='/home/andrew/work/hh.sites.main/config/frontik_dev.cfg'
)
