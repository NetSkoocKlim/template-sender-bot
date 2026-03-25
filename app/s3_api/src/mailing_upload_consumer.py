import logging

import aiohttp
from aio_pika.abc import AbstractIncomingMessage
from aiohttp import FormData
from sqlalchemy.ext.asyncio import AsyncSession

from app.s3_api.src.mailing_result_sender import MailingResultSender
from app.s3_api.src.mailing_retry_sender import MailingRetrySender
from shared.src.database import DBHelper
from shared.src.rabbitmq.base_consumer import BaseConsumer
from shared.src.rabbitmq.message_serializer import MessageSerializer
from shared.src.rabbitmq.schemas import UploadMailingCommand, MailingUploadResultEvent
from shared.src.rabbitmq.topology_manager import RabbitTopologyManager
from shared.src.rabbitmq.routes import Queues
from shared.src.rabbitmq.exceptions import RetryableProcessingError

import base64

logger = logging.getLogger(__name__)

class MailingUploadConsumer(BaseConsumer):
    def __init__(
            self,
            topology_manager: RabbitTopologyManager,
            mailing_result_publisher: MailingResultSender,
            retry_publisher: MailingRetrySender,
            queue_name: str = Queues.MAILINGS_SAVE,
            max_upload_attempts: int = 10,
    ):
        super().__init__(topology_manager, queue_name)
        self._mailing_result_publisher = mailing_result_publisher
        self._retry_publisher = retry_publisher
        self._max_attempts = max_upload_attempts

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
                async with session.post(
                    "http://0.0.0.0:8000/api/upload",
                    data=data
                ) as resp:
                    data = await resp.json()

                    await self._mailing_result_publisher.publish_mailing_result(MailingUploadResultEvent(
                        sender_id=payload.sender_id,
                        mailing_id=payload.mailing_id,
                        file_name=payload.file_name,
                        s3_key=data["key"],
                    ))
        except RetryableProcessingError as exc:
            await self._handle_retryable_error(message, exc)
        except Exception as e:
            await self._handle_non_retryable_error(message, e)
            pass
        finally:
            await message.ack()

    async def _handle_retryable_error(
            self,
            message: AbstractIncomingMessage,
            exc: Exception,
    ) -> None:
        payload = MessageSerializer.decode_model(message, UploadMailingCommand)

        next_attempt = payload.attempt + 1

        if next_attempt < self._max_attempts:
            retry_command = payload.model_copy(update={"attempt": next_attempt})
            delay_ms = self._get_retry_delay_ms(next_attempt)
            logger.warning(
                "Retry upload mailing sender_id=%s mailing_id=%s attempt=%s delay_ms=%s error=%s",
                payload.sender_id,
                payload.mailing_id,
                next_attempt,
                delay_ms,
                str(exc),
            )

            await self._retry_publisher.retry_upload_mailing(
                retry_command,
                delay_ms
            )
        else:
            await self._handle_non_retryable_error(message, exc)

    async def _handle_non_retryable_error(
            self,
            message: AbstractIncomingMessage,
            exc: Exception,
    ) -> None:
        payload = MessageSerializer.decode_model(message, UploadMailingCommand)
        await self._mailing_result_publisher.publish_mailing_result(
            MailingUploadResultEvent(
                sender_id=payload.sender_id,
                mailing_id=payload.mailing_id,
                file_name=payload.file_name,
                error_message=f"Upload failed after {self._max_attempts} attempts: {exc}",
            )
        )


    @staticmethod
    def _get_retry_delay_ms(attempt: int) -> int:
        return 30_000 * (2 ** (attempt - 1))