from typing import Callable, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from database.redis import get_redis
from database.redis.redis_keys import user_requestlimit_key


class RequestLimitMiddleware(BaseMiddleware):

    async def __call__(self,
                 handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
                 event: TelegramObject,
                 data: dict[str, Any]):
        user: User = data.get('event_from_user')
        if not user or not user.id:
            return await handler(event, data)

        allowed = await self._allow(user.id)
        if not allowed:
            return None
        try:
            return await handler(event, data)
        finally:
            await get_redis().delete(user_requestlimit_key(user.id))

    @staticmethod
    async def _allow(user_id: int) -> bool:
        try:
            ok = await get_redis().set(user_requestlimit_key(user_id), 1, nx=True)
            return bool(ok)
        except Exception as e:
            return False