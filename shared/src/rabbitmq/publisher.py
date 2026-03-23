from .message_serializer import MessageSerializer
from .schemas import BaseMessageModel
from .topology_manager import RabbitTopologyManager


class RabbitPublisher:
    def __init__(
        self,
        topology_manager: RabbitTopologyManager,
    ):
        self._topology_manager = topology_manager

    async def _publish(
            self,
            exchange_name: str,
            routing_key: str,
            payload: BaseMessageModel,
    ):
        exchange = self._topology_manager.get_exchange(exchange_name)
        message = MessageSerializer.encode(payload)

        await exchange.publish(message, routing_key=routing_key)