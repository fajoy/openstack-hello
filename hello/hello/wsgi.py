import os
from paste import deploy
from oslo.config import cfg
from openstack.common import excutils
from openstack.common.gettextutils import _
from openstack.common import log as logging

import webob
import eventlet
import eventlet.wsgi
import greenlet
import socket


# Raise the default from 8192 to accommodate large tokens
eventlet.wsgi.MAX_HEADER_LINE = 16384

wsgi_opts = [
    cfg.StrOpt('api_paste_config',
               default="api-paste.ini",
               help='File name for the paste.deploy config for nova-api'),
    cfg.StrOpt('wsgi_log_format',
            default='%(client_ip)s "%(request_line)s" status: %(status_code)s'
                    ' len: %(body_length)s time: %(wall_seconds).7f',
            help='A python format string that is used as the template to '
                 'generate log lines. The following values can be formatted '
                 'into it: client_ip, date_time, request_line, status_code, '
                 'body_length, wall_seconds.'),
    cfg.StrOpt('ssl_ca_file',
               help="CA certificate file to use to verify "
                    "connecting clients"),
    cfg.StrOpt('ssl_cert_file',
                    help="SSL certificate of API server"),
    cfg.StrOpt('ssl_key_file',
                    help="SSL private key of API server"),
    cfg.IntOpt('tcp_keepidle',
               default=600,
               help="Sets the value of TCP_KEEPIDLE in seconds for each "
                    "server socket. Not supported on OS X.")
    ]
CONF = cfg.CONF
CONF.register_opts(wsgi_opts)

LOG = logging.getLogger(__name__)


class Loader(object):
    """Used to load WSGI applications from paste configurations."""

    def __init__(self, config_path=None):
        """Initialize the loader, and attempt to find the config.

        :param config_path: Full or relative path to the paste config.
        :returns: None

        """
        config_path = config_path or CONF.api_paste_config
        if os.path.exists(config_path):
            self.config_path = config_path
        else:
            self.config_path = CONF.find_file(config_path)

    def load_app(self, name):
        """Return the paste URLMap wrapped WSGI application.

        :param name: Name of the application to load.
        :returns: Paste URLMap object wrapping the requested application.
        """
        LOG.debug(_("Loading app %(name)s from %(path)s") %
                      {'name': name, 'path': self.config_path})
        return deploy.loadapp("config:%s" % self.config_path, name=name)

class Request(webob.Request):

    def best_match_content_type(self):
        """Determine the most acceptable content-type.

        Based on:
            1) URI extension (.json/.xml)
            2) Content-type header
            3) Accept* headers
        """
        # First lookup http request path
        parts = self.path.rsplit('.', 1)
        if len(parts) > 1:
            _format = parts[1]
            if _format in ['json', 'xml']:
                return 'application/{0}'.format(_format)

        #Then look up content header
        type_from_header = self.get_content_type()
        if type_from_header:
            return type_from_header
        ctypes = ['application/json', 'application/xml']

        #Finally search in Accept-* headers
        bm = self.accept.best_match(ctypes)
        return bm or 'application/json'


    def get_content_type(self):
        allowed_types = ("application/xml", "application/json")
        if "Content-Type" not in self.headers:
            LOG.debug(_("Missing Content-Type"))
            return None
        _type = self.content_type
        if _type in allowed_types:
            return _type
        return None


class Server(object):
    """Server class to manage a WSGI server, serving a WSGI application."""

    default_pool_size = 1000

    def __init__(self, name, app, host='0.0.0.0', port=0, pool_size=None,
                       protocol=eventlet.wsgi.HttpProtocol, backlog=128,
                       use_ssl=False, max_url_len=None):
        """Initialize, but do not start, a WSGI server.

        :param name: Pretty name for logging.
        :param app: The WSGI application to serve.
        :param host: IP address to serve the application.
        :param port: Port number to server the application.
        :param pool_size: Maximum number of eventlets to spawn concurrently.
        :param backlog: Maximum number of queued connections.
        :param max_url_len: Maximum length of permitted URLs.
        :returns: None
        :raises: nova.exception.InvalidInput
        """
        self.name = name
        self.app = app
        self._server = None
        self._protocol = protocol
        self._pool = eventlet.GreenPool(pool_size or self.default_pool_size)
        self._logger = logging.getLogger("%s.wsgi.server" % self.name)
        self._wsgi_logger = logging.WritableLogger(self._logger)
        self._use_ssl = use_ssl
        self._max_url_len = max_url_len

        if backlog < 1:
            raise exception.InvalidInput(
                    reason='The backlog must be more than 1')

        bind_addr = (host, port)
        # TODO(dims): eventlet's green dns/socket module does not actually
        # support IPv6 in getaddrinfo(). We need to get around this in the
        # future or monitor upstream for a fix
        try:
            info = socket.getaddrinfo(bind_addr[0],
                                      bind_addr[1],
                                      socket.AF_UNSPEC,
                                      socket.SOCK_STREAM)[0]
            family = info[0]
            bind_addr = info[-1]
        except Exception:
            family = socket.AF_INET

        self._socket = eventlet.listen(bind_addr, family, backlog=backlog)
        (self.host, self.port) = self._socket.getsockname()[0:2]
        LOG.info(_("%(name)s listening on %(host)s:%(port)s") % self.__dict__)

    def start(self):
        """Start serving a WSGI application.

        :returns: None
        """
        if self._use_ssl:
            try:
                ca_file = CONF.ssl_ca_file
                cert_file = CONF.ssl_cert_file
                key_file = CONF.ssl_key_file

                if cert_file and not os.path.exists(cert_file):
                    raise RuntimeError(
                          _("Unable to find cert_file : %s") % cert_file)

                if ca_file and not os.path.exists(ca_file):
                    raise RuntimeError(
                          _("Unable to find ca_file : %s") % ca_file)

                if key_file and not os.path.exists(key_file):
                    raise RuntimeError(
                          _("Unable to find key_file : %s") % key_file)

                if self._use_ssl and (not cert_file or not key_file):
                    raise RuntimeError(
                          _("When running server in SSL mode, you must "
                            "specify both a cert_file and key_file "
                            "option value in your configuration file"))
                ssl_kwargs = {
                    'server_side': True,
                    'certfile': cert_file,
                    'keyfile': key_file,
                    'cert_reqs': ssl.CERT_NONE,
                }

                if CONF.ssl_ca_file:
                    ssl_kwargs['ca_certs'] = ca_file
                    ssl_kwargs['cert_reqs'] = ssl.CERT_REQUIRED

                self._socket = eventlet.wrap_ssl(self._socket,
                                                 **ssl_kwargs)

                self._socket.setsockopt(socket.SOL_SOCKET,
                                        socket.SO_REUSEADDR, 1)
                # sockets can hang around forever without keepalive
                self._socket.setsockopt(socket.SOL_SOCKET,
                                        socket.SO_KEEPALIVE, 1)

                # This option isn't available in the OS X version of eventlet
                if hasattr(socket, 'TCP_KEEPIDLE'):
                    self._socket.setsockopt(socket.IPPROTO_TCP,
                                    socket.TCP_KEEPIDLE,
                                    CONF.tcp_keepidle)

            except Exception:
                with excutils.save_and_reraise_exception():
                    LOG.error(_("Failed to start %(name)s on %(host)s"
                                ":%(port)s with SSL support") % self.__dict__)

        wsgi_kwargs = {
            'func': eventlet.wsgi.server,
            'sock': self._socket,
            'site': self.app,
            'protocol': self._protocol,
            'custom_pool': self._pool,
            'log': self._wsgi_logger,
            'log_format': CONF.wsgi_log_format
            }

        if self._max_url_len:
            wsgi_kwargs['url_length_limit'] = self._max_url_len

        self._server = eventlet.spawn(**wsgi_kwargs)

    def stop(self):
        """Stop this server.

        This is not a very nice action, as currently the method by which a
        server is stopped is by killing its eventlet.

        :returns: None

        """
        LOG.info(_("Stopping WSGI server."))

        if self._server is not None:
            # Resize pool to stop new requests from being processed
            self._pool.resize(0)
            self._server.kill()

    def wait(self):
        """Block, until the server has stopped.

        Waits on the server's eventlet to finish, then returns.

        :returns: None

        """
        try:
            self._server.wait()
        except greenlet.GreenletExit:
            LOG.info(_("WSGI server has stopped."))


