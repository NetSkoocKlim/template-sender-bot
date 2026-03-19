import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.methods import DeleteWebhook
from aiogram.enums import ParseMode

from bot.middelwares.database_middleware import DatabaseMiddleware
from bot.middelwares.user_middleware import UserMiddleware
from database.migrations import run_alembic_upgrade
from database.redis import init_redis, close_redis, get_redis
from bot.middelwares.throttling_middleware import ThrottlingMiddleware
from bot.middelwares.requestlimit_middleware import RequestLimitMiddleware
from bot.handlers import router as main_router
from config import settings
from services.object_storage_app.app import ObjectStorageApp

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')



async def on_startup(dispatcher: Dispatcher):

    redis = await get_redis()
    dispatcher["redis"] = redis
    s3_storage = ObjectStorageApp()
    dispatcher["s3_storage"] = s3_storage

async def on_shutdown(dispatcher: Dispatcher):
    redis = dispatcher.get("redis")
    if redis:
        await close_redis()

async def main():
    skip_migration = os.getenv('SKIP_MIGRATION', 'false').lower() == 'true'
    if not skip_migration:
        await run_alembic_upgrade()
    bot = Bot(token=settings.bot.TOKEN, default=DefaultBotProperties(
        parse_mode=ParseMode.HTML))

    redis = await init_redis()
    dp = Dispatcher(storage=RedisStorage(redis=redis))

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    dp.message.outer_middleware(ThrottlingMiddleware())
    dp.callback_query.outer_middleware(ThrottlingMiddleware())
    dp.update.outer_middleware(RequestLimitMiddleware())

    dp.update.outer_middleware(DatabaseMiddleware())
    dp.message.outer_middleware(UserMiddleware())
    dp.callback_query.outer_middleware(UserMiddleware())

    dp.include_router(main_router)
    await bot(method=DeleteWebhook(drop_pending_updates=True))
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
