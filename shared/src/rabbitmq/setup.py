from .channel_manager import RabbitChannelManager
from .connection_manager import RabbitConnectionManager
from .topology_manager import RabbitTopologyManager

connection_manager: RabbitConnectionManager | None = None
channel_manager: RabbitChannelManager | None= None
topology_manager: RabbitTopologyManager | None = None

async def init_rabbit_connection():
    global connection_manager, channel_manager, topology_manager
    if not connection_manager:
        connection_manager = RabbitConnectionManager()
    if not channel_manager:
        channel_manager = RabbitChannelManager(connection_manager)
    if not topology_manager:
        topology_manager = RabbitTopologyManager(channel_manager)

    await connection_manager.connect()
    await channel_manager.open()
    await topology_manager.setup()


async def close_rabbit_connection():
    global connection_manager, channel_manager, topology_manager
    try:
        await channel_manager.close()
        await connection_manager.close()
    finally:
        connection_manager, channel_manager, topology_manager = None, None, None


def get_topology_manager():
    return topology_manager