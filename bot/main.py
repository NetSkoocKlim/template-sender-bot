import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.methods import DeleteWebhook
from aiogram.enums import ParseMode
from database.redis import init_redis, close_redis, get_redis
from bot.middelwares.ratelimit_middleware import RateLimitMiddleware
from bot.middelwares.requestlimit_middleware import RequestLimitMiddleware
from handlers import router as main_router
from config import settings

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
bot = Bot(token=settings.bot.TOKEN, default=DefaultBotProperties(
          parse_mode=ParseMode.HTML))

async def on_startup(dispatcher: Dispatcher):
    redis = await get_redis()
    dispatcher["redis"] = redis

async def on_shutdown(dispatcher: Dispatcher):
    redis = dispatcher.get("redis")
    if redis:
        await close_redis()

async def main():
    redis = await init_redis()
    dp = Dispatcher(storage=RedisStorage(redis=redis))

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    dp.include_router(main_router)
    # dp.update.outer_middleware(RateLimitMiddleware())
    # dp.update.outer_middleware(RequestLimitMiddleware())
    await bot(method=DeleteWebhook(drop_pending_updates=True))
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
