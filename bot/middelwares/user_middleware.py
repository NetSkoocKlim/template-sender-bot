from typing import Callable, Awaitable, Any

from aiogram import BaseMiddleware
from aiogram.filters.callback_data import CallbackData
from aiogram.types import TelegramObject

from database.models import User as DBUser
from aiogram.types import User

class UserMiddleware(BaseMiddleware):

    async def __call__(
            self,
            handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: dict[str, Any]
    ):
        session = data.get("session")
        user: User = data.get('event_from_user')
        if not session or not user:
            return await handler(event, data)
        saved_user = await DBUser.get(
            session=session,
            primary_key=user.id
        )
        if not saved_user:
            await DBUser.create(
                session=session,
                username=user.username,
            )
        if saved_user.username != user.username:
            setattr(saved_user, "username", user.username)
        return await handler(event, data)






