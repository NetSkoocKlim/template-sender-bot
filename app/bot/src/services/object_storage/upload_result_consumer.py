import logging

from aio_pika.abc import AbstractIncomingMessage
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from shared.src.database import DBHelper
from shared.src.database.models import Mailing
from shared.src.database.models.mailing import MailingStatus
from shared.src.rabbitmq.base_consumer import BaseConsumer
from shared.src.rabbitmq.message_serializer import MessageSerializer
from shared.src.rabbitmq.schemas import MailingUploadResultEvent
from shared.src.rabbitmq.topology_manager import RabbitTopologyManager
from shared.src.rabbitmq.routes import Queues

logger = logging.getLogger()
class MailingUploadResultConsumer(BaseConsumer):
    def __init__(
        self,
        topology_manager: RabbitTopologyManager,
        bot: Bot,
        queue_name: str = Queues.MAILING_RESULTS,
    ):
        super().__init__(topology_manager, queue_name)
        self._bot = bot

    @DBHelper.get_session
    async def _on_message(self, message: AbstractIncomingMessage, session: AsyncSession):
        try:
            payload: MailingUploadResultEvent = MessageSerializer.decode_model(
                message,
                MailingUploadResultEvent
            )
            if payload.error_message:
                await self._bot.send_message(
                    text=f"Не удалось сохранить результат рассылки: {payload.error_message}",
                    chat_id=payload.sender_id,
                )
                await Mailing.update(
                    session=session,
                    primary_key=payload.mailing_id,
                    save_status=MailingStatus.FAILED.value,
                )
                return

            await Mailing.update(
                session=session,
                primary_key=payload.mailing_id,
                s3_key=payload.s3_key,
                save_status=MailingStatus.SAVED.value
            )
        except Exception as e:
            logger.error(f"Error while handling mailing save result: {e}")

        finally:
            await message.ack()




