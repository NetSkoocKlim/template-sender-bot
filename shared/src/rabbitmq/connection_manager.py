import logging

import aio_pika
from aio_pika.abc import AbstractRobustConnection

from config import settings

logger = logging.getLogger(__name__)

class RabbitConnectionManager:
    def __init__(self):
        self._config = settings.rabbitmq
        self._connection: AbstractRobustConnection | None = None

    async def connect(self) -> AbstractRobustConnection | None:
        if self._connection and not self._connection.is_closed:
            return self._connection
        logger.info("[ ] Connecting to RabbitMQ")
        self._connection = await aio_pika.connect_robust(
            self._config.url
        )
        logger.info("[✓] Connected: %r", self._connection)
        return self._connection

    async def get_connection(self) -> AbstractRobustConnection:
        if self._connection is None or self._connection.is_closed:
            raise RuntimeError("RabbitMQ connection is not established")
        return self._connection

    async def close(self) -> None:
        if self._connection and not self._connection.is_closed:
            await self._connection.close()