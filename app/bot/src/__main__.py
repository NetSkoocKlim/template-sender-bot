import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.methods import DeleteWebhook
from aiogram.enums import ParseMode

from app.bot.src.services.object_storage.app import ObjectStorage
from app.bot.src.services.object_storage.csv_sender import MailingSender
from app.bot.src.services.object_storage.upload_result_consumer import MailingUploadResultConsumer
from shared.src.rabbitmq.setup import init_rabbit_connection, get_topology_manager, close_rabbit_connection
from .middelwares.database_middleware import DatabaseMiddleware
from .middelwares.user_middleware import UserMiddleware
from .middelwares.throttling_middleware import ThrottlingMiddleware
from .middelwares.requestlimit_middleware import RequestLimitMiddleware
from .handlers import router as main_router

from shared.src.database.migrations import run_alembic_upgrade
from shared.src.redis import init_redis, close_redis, get_redis
from config import settings

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


async def on_startup(dispatcher: Dispatcher):
    redis = await get_redis()
    dispatcher["redis"] = redis
    await init_rabbit_connection()
    topology_manager = get_topology_manager()
    mailing_sender = MailingSender(topology_manager)
    mailing_result_consumer = MailingUploadResultConsumer(
        topology_manager=topology_manager,
        bot=dispatcher["bot"]
    )
    s3_storage = ObjectStorage(mailing_sender)
    dispatcher["mailing_sender"] = mailing_sender
    dispatcher["s3_storage"] = s3_storage
    await mailing_result_consumer.start()


async def on_shutdown(dispatcher: Dispatcher):
    await close_redis()
    await close_rabbit_connection()



async def main():
    skip_migration = os.getenv('SKIP_MIGRATION', 'false').lower() == 'true'
    if not skip_migration:
        await run_alembic_upgrade()
    bot = Bot(token=settings.bot.TOKEN, default=DefaultBotProperties(
        parse_mode=ParseMode.HTML))

    redis = await init_redis()
    dp = Dispatcher(storage=RedisStorage(redis=redis), bot=bot)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    dp.message.outer_middleware(ThrottlingMiddleware())
    dp.callback_query.outer_middleware(ThrottlingMiddleware())
    dp.message.outer_middleware(RequestLimitMiddleware())
    dp.callback_query.outer_middleware(RequestLimitMiddleware())


    dp.update.outer_middleware(DatabaseMiddleware())
    dp.message.outer_middleware(UserMiddleware())
    dp.callback_query.outer_middleware(UserMiddleware())

    dp.include_router(main_router)
    await bot(method=DeleteWebhook(drop_pending_updates=True))
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
