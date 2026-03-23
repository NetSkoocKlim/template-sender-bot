import logging
from aio_pika.abc import AbstractExchange, AbstractQueue, ExchangeType

from .channel_manager import RabbitChannelManager
from .routes import QueueBinding, Exchanges, Bindings


logger = logging.getLogger(__name__)

class RabbitTopologyManager:
    def __init__(self, channel_manager: RabbitChannelManager) -> None:
        self._channel_manager = channel_manager
        self._exchanges: dict[str, AbstractExchange] = {}
        self._queues: dict[str, AbstractQueue] = {}
        self._bindings: list[QueueBinding] = []


    async def setup(self) -> None:
        channel = await self._channel_manager.get_channel()
        logger.info("[ ] Initializing RabbitTopologyManager")
        events_exchange = await channel.declare_exchange(
            Exchanges.MAILINGS,
            ExchangeType.DIRECT,
            durable=True,
        )

        self._exchanges[events_exchange.name] = events_exchange
        for binding in Bindings.ALL:
            await self._declare_and_bind_queue(binding)
        logger.info("[] RabbitTopologyManager was successfully initialized %r", self)



    async def _declare_and_bind_queue(self, binding: QueueBinding) -> None:
        channel = await self._channel_manager.get_channel()

        queue = await channel.declare_queue(
            name=binding.queue,
            durable=binding.durable,
            exclusive=binding.exclusive,
            auto_delete=binding.auto_delete,
        )

        exchange = self.get_exchange(binding.exchange)
        await queue.bind(exchange=exchange, routing_key=binding.routing_key)

        self._queues[binding.queue] = queue
        self._bindings.append(binding)


    def get_exchange(self, name):
        exchange = self._exchanges.get(name)
        if exchange is None:
            raise RuntimeError(f"Exchange '{name}' is not declared")
        return exchange


    def get_queue(self, name):
        queue = self._queues.get(name)
        if queue is None:
            raise RuntimeError(f"Queue '{name}' is not declared")
        return queue
