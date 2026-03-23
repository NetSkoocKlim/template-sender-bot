from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from pydantic import BaseModel
from aio_pika.abc import AbstractIncomingMessage

from .message_serializer import MessageSerializer
from .topology_manager import RabbitTopologyManager


ModelT = TypeVar("ModelT", bound=BaseModel)


class BaseConsumer(ABC):
    def __init__(
        self,
        topology_manager: RabbitTopologyManager,
        queue_name: str,
    ) -> None:
        self._topology_manager = topology_manager
        self._queue_name = queue_name

    async def start(self) -> None:
        queue = self._topology_manager.get_queue(self._queue_name)
        await queue.consume(self._on_message)

    @abstractmethod
    async def _on_message(self, message: AbstractIncomingMessage) -> None:
        pass
