from typing import Callable, Dict, Any, Awaitable

from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from database import DBHelper


@DBHelper.get_session
async def database_middleware(handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
                              event: TelegramObject,
                              data: Dict[str, Any],
                              session: AsyncSession
                              ):
    data['session'] = session
    await handler(event, data)

