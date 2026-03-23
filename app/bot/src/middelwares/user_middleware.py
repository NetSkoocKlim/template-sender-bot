import logging
from typing import Callable, Awaitable, Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from shared.src.database.models import User as DBUser
from aiogram.types import User

logger = logging.getLogger(__name__)

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
        if saved_user:
            if saved_user.username != user.username:
                logger.info("User %s has changed his username to %s", saved_user, user.username)
                setattr(saved_user, "username", user.username)
        else:
            logger.info("Adding a new user to db %s", user.username)
            await DBUser.create(
                id=user.id,
                session=session,
                username=user.username,
            )
        return await handler(event, data)






