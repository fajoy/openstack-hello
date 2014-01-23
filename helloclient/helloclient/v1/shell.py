from helloclient.openstack.common import cliutils as utils
def do_list(hc, args):
    """Show details about a volume."""
    columns = [
            "ID",
            'Name',
            "Description",
        ]

    worlds = hc.hello.worlds.list()
    formatters = {}
    utils.print_list(worlds, columns, formatters)

@utils.arg('world',
     metavar='<world-id>',
     help="Name or ID of world")
def do_world(hc, args):
    """Show details about a world."""
    world = hc.hello.worlds.get(args.world)
    info = world._info.copy()
    utils.print_dict(info)
