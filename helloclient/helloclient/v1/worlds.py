from helloclient.openstack.common.apiclient import base
class WorldSet(base.Resource):
    def __repr__(self):
        return "<World: %s>" % self.id

class WorldSetManager(base.ManagerWithFind):
    resource_class = WorldSet

    def get(self, world_id):
        """
        Get a world.

        :param world_id: The ID of the world.
        :rtype: :class:`World`
        """
        return self._get("/worlds/%s" % world_id, "world")

    def list(self):
        """
        Get a list of all worlds.

        :rtype: list of :class:`World`
        """
        return self._list("/worlds/detail","worlds")
