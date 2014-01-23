import webob.dec
from hello.openstack.common import gettextutils
from hello.openstack.common import log as logging
from hello import wsgi
LOG = logging.getLogger(__name__)

class Versions(object):

    @classmethod
    def factory(cls, global_config, **local_config):
        return cls()

    @webob.dec.wsgify(RequestClass=webob.Request)
    def __call__(self, req):
        """Respond to a request for all Hello API versions."""
        version_objs = [
            {
                "id": "v1.0",
                "status": "CURRENT",
            },
        ]

        metadata = {
            "application/xml": {
                "attributes": {
                    "version": ["status", "id"],
                    "link": ["rel", "href"],
                }
            }
        }

        content_type = "application/xml"
        body="""<?xml version='1.0' encoding='UTF-8'?>
<versions xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><version><status>CURRENT</status><id>v1.0</id></version></versions>
"""
        response = webob.Response()
        response.content_type = content_type
        response.body = body
        return response
