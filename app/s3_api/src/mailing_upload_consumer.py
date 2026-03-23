import logging

import aiohttp
from aio_pika.abc import AbstractIncomingMessage
from aiohttp import FormData

from app.s3_api.src.mailing_result_sender import MailingResultSender
from config import settings
from shared.src.rabbitmq.base_consumer import BaseConsumer
from shared.src.rabbitmq.message_serializer import MessageSerializer
from shared.src.rabbitmq.schemas import UploadMailingCommand, MailingUploadResultEvent
from shared.src.rabbitmq.topology_manager import RabbitTopologyManager
from shared.src.rabbitmq.routes import Queues

import base64

logger = logging.getLogger(__name__)

class MailingUploadConsumer(BaseConsumer):
    def __init__(
            self,
            topology_manager: RabbitTopologyManager,
            mailing_result_publisher: MailingResultSender,
            queue_name: str = Queues.MAILINGS_SAVE,
    ):
        super().__init__(topology_manager, queue_name)
        self._mailing_result_publisher = mailing_result_publisher

    async def _on_message(self, message: AbstractIncomingMessage) -> None:
        try:
            payload = MessageSerializer.decode_model(
                message,
                UploadMailingCommand
            )
            csv_bytes = base64.b64decode(payload.file_bytes_b64)
            data = FormData()
            data.add_field(
                "file",
                csv_bytes,
                content_type="application/octet-stream"
            )
            data.add_field(
                "key",
                f"mailing-result-{payload.sender_id}-{payload.mailing_id}"
            )
            async with aiohttp.ClientSession() as session:
                async with session.get("http://0.0.0.0:8000/api/s3_health") as resp:
                    health_check_data = await resp.json()
                    if not health_check_data["ok"]:
                        ...
                        raise
                async with session.post(
                    "http://0.0.0.0:8000/api/upload",
                    data=data
                ) as resp:
                    data = await resp.json()

                    await self._mailing_result_publisher.publish_success_mailing_result(
                        MailingUploadResultEvent(
                            sender_id=payload.sender_id,
                            mailing_id=payload.mailing_id,
                            file_name=payload.file_name,
                            s3_key=data["key"],
                        )
                    )

        except Exception as e:
            logger.error(e)
            pass
        finally:
            await message.ack()
