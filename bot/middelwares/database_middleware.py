from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from database import DBHelper
from typing import Any, Dict
from aiogram.types.base import TelegramObject


class DatabaseMiddleware(BaseMiddleware):

    @DBHelper.get_session
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
        session: AsyncSession,
    ) -> Any:
        data['session'] = session
        return await handler(event, data)
