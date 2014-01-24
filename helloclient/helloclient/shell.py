#!/usr/bin/env python
"""
Command-line interface to the OpenStack Hello API.
"""
if __name__ == '__main__' and __package__ is None:
    from os import sys, path
    sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

import sys
import argparse
import logging
import sys

from helloclient.openstack.common.apiclient import auth
from keystoneclient.v2_0 import client as ksclient
from helloclient.openstack.common import cliutils as utils
from helloclient.openstack.common import strutils
from helloclient import client as helloclient
from helloclient.openstack.common.apiclient import client
from helloclient.openstack.common.apiclient import exceptions as exc

from helloclient.v1 import shell as shell_v1
api_version="1"

logger = logging.getLogger(__name__)

class HelpFormatter(argparse.HelpFormatter):
    def start_section(self, heading):
        # Title-case the headings
        heading = '%s%s' % (heading[0].upper(), heading[1:])
        super(HelpFormatter, self).start_section(heading)

class KeystoneAuthPlugin(auth.BaseAuthPlugin):
    opt_names =[
        "username",
        "password",
        "tenant_name",
        "auth_url",
    ]
    def __init__(self,*args,**kwargs):
        super(self.__class__,self).__init__(*args,**kwargs)
        self._kwargs=kwargs
    
    def _do_authenticate(self, http_client):
        """Protected method for authentication.
        """
        ks_kwargs = {
            'username': self.opts.get('username'),
            'password': self.opts.get('password'),
            'tenant_name': self.opts.get('tenant_name'),
            'auth_url': self.opts.get('auth_url'),
        }
        self._http_client = http_client
        self._ksclient = ksclient.Client(**ks_kwargs)

    def token_and_endpoint(self, endpoint_type, service_type):
        """Return token and endpoint.

        :param service_type: Service type of the endpoint
        :type service_type: string
        :param endpoint_type: Type of endpoint.
                              Possible values: public or publicURL,
                                  internal or internalURL,
                                  admin or adminURL
        :type endpoint_type: string
        :returns: tuple of token and endpoint strings
        :raises: EndpointException
        """
        if not hasattr(self, '_ksclient'):
            return (None, None)

        token = self._ksclient.auth_token
        endpoint = (self._kwargs.get('hello_url') or
                    self._ksclient.service_catalog.url_for(
                        service_type=service_type,
                        endpoint_type=endpoint_type))
        return (token, endpoint)

class OpenStackHelloShell(object):
    def get_base_parser(self):
        parser = argparse.ArgumentParser(
            prog='hello',
            description=__doc__.strip(),
            epilog='See "hello help COMMAND" '
                   'for help on a specific command.',
            add_help=False,
            formatter_class=HelpFormatter,
        )

        # Global arguments
        parser.add_argument('-h', '--help',
                            action='store_true',
                            help=argparse.SUPPRESS,
                            )

        parser.add_argument('--version',
                            action='version',
                            version='1.0.0')

        parser.add_argument('-d', '--debug',
                            default=False,
                            action='store_true',
                            help='Defaults to env[GLANCECLIENT_DEBUG]')

        parser.add_argument('-v', '--verbose',
                            default=False, action="store_true",
                            help="Print more verbose output")

        parser.add_argument('-k', '--insecure',
                            default=False,
                            action='store_true',
                            help='Explicitly allow glanceclient to perform '
                            '\"insecure SSL\" (https) requests. The server\'s '
                            'certificate will not be verified against any '
                            'certificate authorities. This option should '
                            'be used with caution.')

        KeystoneAuthPlugin.add_opts(parser)
        KeystoneAuthPlugin.add_common_opts(parser)
        parser.add_argument('--os-hello-url',
                            default=utils.env('OS_HELLO_URL'),
                            help='Defaults to env[OS_HELLO_URL]')

        return parser

    def get_subcommand_parser(self, version):
        parser = self.get_base_parser()

        self.subcommands = {}
        subparsers = parser.add_subparsers(metavar='<subcommand>')

        try:
            actions_module = {
                '1': shell_v1,
            }[version]
        except KeyError:
            actions_module = shell_v1

        self._find_actions(subparsers, actions_module)
        self._find_actions(subparsers, self)
        return parser

    def _find_actions(self, subparsers, actions_module):
        for attr in (a for a in dir(actions_module) if a.startswith('do_')):
            # I prefer to be hypen-separated instead of underscores.
            command = attr[3:].replace('_', '-')
            callback = getattr(actions_module, attr)
            desc = callback.__doc__ or ''
            help = desc.strip().split('\n')[0]
            arguments = getattr(callback, 'arguments', [])

            subparser = subparsers.add_parser(command,
                                              help=help,
                                              description=desc,
                                              add_help=False,
                                              formatter_class=HelpFormatter
                                              )
            subparser.add_argument('-h', '--help',
                                   action='help',
                                   help=argparse.SUPPRESS,
                                   )
            self.subcommands[command] = subparser
            for (args, kwargs) in arguments:
                subparser.add_argument(*args, **kwargs)
            subparser.set_defaults(func=callback)

    @utils.arg('command', metavar='<subcommand>', nargs='?',
               help='Display help for <subcommand>')
    def do_help(self, args):
        """Display help about this program or one of its subcommands."""
        if getattr(args, 'command', None):
            if args.command in self.subcommands:
                self.subcommands[args.command].print_help()
            else:
                raise exc.CommandError("'%s' is not a valid subcommand" %
                                       args.command)
        else:
            self.parser.print_help()

    def main(self, argv):
        # Parse args once to find version
        parser = self.get_base_parser()
        (options, args) = parser.parse_known_args(argv)

        # build available subcommands based on version
        subcommand_parser = self.get_subcommand_parser(api_version)
        self.parser = subcommand_parser

        # Handle top-level --help/-h before attempting to parse
        # a command off the command line
        if options.help or not argv:
            self.do_help(options)
            return 0

        # Parse args again and call whatever callback was selected
        args = subcommand_parser.parse_args(argv)

        # Short-circuit and deal with help command right away.
        if args.func == self.do_help:
            self.do_help(args)
            return 0
        kwargs = {
            'username': args.os_username,
            'password': args.os_password,
            'tenant_name': args.os_tenant_name,
            'auth_url': args.os_auth_url,
            'insecure': args.insecure,
            'hello_url': args.os_hello_url,
        }
        auth = KeystoneAuthPlugin(auth_system="keystone",**kwargs)
        openstack_client = client.HTTPClient(auth)
        helloclient.Client(api_version ,openstack_client)
        try:
            args.func(openstack_client, args)
        except exc.Unauthorized:
            raise exc.CommandError("Invalid OpenStack Identity credentials.")

def main():
    try:
        OpenStackHelloShell().main(map(strutils.safe_decode, sys.argv[1:]))
    except KeyboardInterrupt:
        print >> sys.stderr, '... terminating hello client'
        sys.exit(1)
    except Exception as e:
        print >> sys.stderr, e
        sys.exit(1)

if __name__=="__main__":
    main()
