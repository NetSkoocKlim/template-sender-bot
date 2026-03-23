import logging

from aio_pika.abc import AbstractRobustChannel

from shared.src.rabbitmq.connection_manager import RabbitConnectionManager

logger = logging.getLogger(__name__)

class RabbitChannelManager:
    def __init__(self, connection_manager: RabbitConnectionManager) -> None:
        self._connection_manager = connection_manager
        self._channel: AbstractRobustChannel | None = None

    async def open(self) -> AbstractRobustChannel:
        if self._channel and not self._channel.is_closed:
            return self._channel

        logger.info(f"Connecting to RabbitMQ channel")
        connection = await self._connection_manager.get_connection()
        self._channel = await connection.channel()
        logger.info(f"Successfully connected to RabbitMQ channel %r", self._channel)
        return self._channel

    async def get_channel(self) -> AbstractRobustChannel:
        if not self._channel or self._channel.is_closed:
            raise RuntimeError("RabbitMQ channel is not opened")
        return self._channel

    async def close(self) -> None:
        if self._channel and not self._channel.is_closed:
            await self._channel.close()


