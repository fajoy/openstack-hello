import os
from oslo.config import cfg
from hello.openstack.common import service
import logging
from hello import wsgi


LOG = logging.getLogger(__name__)

service_opts = [
    cfg.StrOpt('hello_listen',
               default="0.0.0.0",
               help='IP address for Hello API to listen'),
    cfg.IntOpt('hello_listen_port',
               default=10001,
               help='port for Hello api to listen'),
    cfg.IntOpt('hello_workers',
               help='Number of workers for Hello API service'),
]
CONF = cfg.CONF
CONF.register_opts(service_opts)


class WSGIService(object):
    """Provides ability to launch API from a 'paste' configuration."""

    def __init__(self, name, loader=None, use_ssl=False, max_url_len=None):
        """Initialize, but do not start the WSGI server.

        :param name: The name of the WSGI server given to the loader.
        :param loader: Loads the WSGI application using the given name.
        :returns: None

        """
        self.name = name
        self.manager = self._get_manager()
        self.loader = loader or wsgi.Loader()
        self.app = self.loader.load_app(name)
        self.host = getattr(CONF, '%s_listen' % name, "0.0.0.0")
        self.port = getattr(CONF, '%s_listen_port' % name, 0)
        self.workers = getattr(CONF, '%s_workers' % name, None)
        self.use_ssl = use_ssl
        self.server = wsgi.Server(name,
                                  self.app,
                                  host=self.host,
                                  port=self.port,
                                  use_ssl=self.use_ssl,
                                  max_url_len=max_url_len)
        # Pull back actual port used
        self.port = self.server.port
        self.backdoor_port = None

    def _get_manager(self):
        """Initialize a Manager object appropriate for this service.

        Use the service name to look up a Manager subclass from the
        configuration and initialize an instance. If no class name
        is configured, just return None.

        :returns: a Manager instance, or None.

        """
        fl = '%s_manager' % self.name
        if fl not in CONF:
            return None

        manager_class_name = CONF.get(fl, None)
        if not manager_class_name:
            return None

        manager_class = importutils.import_class(manager_class_name)
        return manager_class()


    def start(self):
        """Start serving this service using loaded configuration.

        Also, retrieve updated port number in case '0' was passed in, which
        indicates a random port should be used.

        :returns: None

        """
        if self.manager:
            self.manager.init_host()
            self.manager.pre_start_hook()
        if self.backdoor_port is not None:
            self.manager.backdoor_port = self.backdoor_port
        self.server.start()
        if self.manager:
            self.manager.post_start_hook()

    def stop(self):
        """Stop serving this API.

        :returns: None

        """
        self.server.stop()

    def wait(self):
        """Wait for the service to stop serving this API.

        :returns: None

        """
        self.server.wait()

