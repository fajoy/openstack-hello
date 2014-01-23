from helloclient.openstack.common.apiclient import client 
from helloclient.v1 import worlds

class Client(client.BaseClient):
    service_type = "hello"
    endpoint_type = "publicURL" 

    def __init__(self, *args, **kwargs):
        super(self.__class__,self).__init__(*args,**kwargs)
        """Initialize a new client for the Hello v1 API."""
        self.worlds = worlds.WorldSetManager(self)
        self.client = self
