import time
from typing import Callable, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, CallbackQuery, Message

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(
        self,
        rate_limit: float = 0.4,
    ):
        self.rate_limit = rate_limit
        self.user_buckets: dict[int, float] = {}

    async def __call__(self,
                 handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
                 event: TelegramObject,
                 data: dict[str, Any]):
        user_id = None
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id
        if not user_id:
            return await handler(event, data)
        now = time.time()
        last_call = self.user_buckets.get(user_id, 0)
        if now - last_call < self.rate_limit:
            if isinstance(event, CallbackQuery):
                await event.answer('⏳ Слишком быстро! Подождите немного.', show_alert=True)
                return None
        self.user_buckets[user_id] = now
        cleanup_threshold = now - 60
        self.user_buckets = {
            uid: timestamp for uid, timestamp in self.user_buckets.items() if timestamp > cleanup_threshold
        }
        return await handler(event, data)
