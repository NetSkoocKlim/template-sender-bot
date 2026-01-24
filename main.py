import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.methods import DeleteWebhook
from aiogram.enums import ParseMode

from handlers import router as main_router
from config import settings

logging.basicConfig(level=logging.INFO)

bot = Bot(token=settings.bot.TOKEN, default=DefaultBotProperties(
          parse_mode=ParseMode.HTML))
dp = Dispatcher()

async def main():
    dp.include_router(main_router)
    await bot(method=DeleteWebhook(drop_pending_updates=True))
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
