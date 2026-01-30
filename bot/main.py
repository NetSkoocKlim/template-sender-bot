import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio.client import Redis
from aiogram.methods import DeleteWebhook
from aiogram.enums import ParseMode

from handlers import router as main_router
from config import settings

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

redis = Redis(
    host=settings.redis.HOST,
    port=settings.redis.PORT,
    db=settings.redis.db,
)

bot = Bot(token=settings.bot.TOKEN, default=DefaultBotProperties(
          parse_mode=ParseMode.HTML))


dp = Dispatcher(storage=RedisStorage(redis=redis))


async def main():
    dp.include_router(main_router)
    await bot(method=DeleteWebhook(drop_pending_updates=True))
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
