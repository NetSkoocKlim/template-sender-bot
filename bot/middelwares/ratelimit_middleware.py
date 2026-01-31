from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from database.redis import redis


class RateLimitMiddleware(BaseMiddleware):
    async def __call__(self,
                 handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
                 event: TelegramObject,
                 data: dict[str, Any]):
        user: User = data.get('event_from_user')
        if not user.id:
            return await handler(event, data)
        allowed = await self._allow(user.id)
        if not allowed:
            return None
        return await handler(event, data)

    async def _allow(self, user_id: int) -> bool:
        key = f"ratelimit:user:{user_id}"
        ok = await redis.set(key, 1, px=500, nx=True)
        return bool(ok)