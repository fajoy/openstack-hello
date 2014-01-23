from helloclient.openstack.common.apiclient import base
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode
import six


class WorldSet(base.Resource):
    def __repr__(self):
        return "<World: %s>" % self.id


class WorldSetManager(base.ManagerWithFind):
    resource_class = WorldSet

    def get(self, world_id):
        """
        Get a world.

        :param world_id: The ID of the world to delete.
        :rtype: :class:`World`
        """
        return self._get("/worlds/%s" % world_id, "world")

    def list(self):
        """
        Get a list of all worlds.

        :rtype: list of :class:`World`
        """
        return self._list("/worlds/detail","worlds")
