import logging

from aio_pika.abc import AbstractIncomingMessage
from aiogram import Bot

from shared.src.database import DBHelper
from shared.src.database.models import Mailing
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

    async def _on_message(self, message: AbstractIncomingMessage):
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
                return
            async with DBHelper.async_session() as session:
                async with session.begin():
                    await Mailing.update(
                        session=session,
                        primary_key=payload.mailing_id,
                        csv_result_key=payload.s3_key,
                    )
            # await self._bot.send_message(
            #     text=f"Результат рассылки ({payload.send_at.strftime("%d.%m.%Y %H:%M:%s")}) был успешно сохранён",
            #     chat_id=payload.sender_id,
            # )
        except Exception as e:
            logger.error(f"Error while handling mailing save result: {e}")

        finally:
            await message.ack()




