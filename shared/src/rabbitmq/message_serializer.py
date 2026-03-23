import json
from typing import Any, TypeVar

from aio_pika import Message, DeliveryMode
from aio_pika.abc import AbstractIncomingMessage

from .schemas import BaseMessageModel

ModelT = TypeVar("ModelT", bound=BaseMessageModel)

class MessageSerializer:
    @staticmethod
    def encode(payload: BaseMessageModel) -> Message:
        return Message(
            body=payload.model_dump_json().encode("utf-8"),
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
        )

    @staticmethod
    def decode_model(
        message: AbstractIncomingMessage,
        model_cls: type[ModelT],
    ) -> ModelT:
        return model_cls.model_validate_json(message.body)
