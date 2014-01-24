#!/usr/bin/env python
import eventlet
import sys
import logging

from hello import config
from hello.openstack.common import log as logging
from hello.openstack.common import service
from hello.service import WSGIService

def main():
    config.parse_args(sys.argv)
    logging.setup("hello")
    eventlet.monkey_patch()
    launcher = service.ProcessLauncher()

    try:
        server = WSGIService("hello")
        launcher.launch_service(server, workers=server.workers or 1)
        launcher.wait()
    except RuntimeError as e:
        sys.exit(_("ERROR: %s") % e)

if __name__ == '__main__':
    main()
