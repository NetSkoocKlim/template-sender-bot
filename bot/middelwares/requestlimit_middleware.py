from typing import Callable, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from database.redis import redis


class RequestLimitMiddleware(BaseMiddleware):
    def __init__(self):
        self.request_user_key_template = "requestlimit:user:{}"

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
            await redis.delete(self._get_user_key(user.id))

    def _get_user_key(self, user_id: int) -> str:
        return self.request_user_key_template.format(user_id)

    async def _allow(self, user_id: int) -> bool:
        try:
            ok = await redis.set(self._get_user_key(user_id), 1, nx=True)
            return bool(ok)
        except Exception as e:
            return False