from aiogram.filters import BaseFilter
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User


class IsAdmin(BaseFilter):
    async def __call__(self, message: Message, *args, session: AsyncSession, **kwargs) -> dict[str, User] | bool:
        user: User = await User.get(session, message.from_user.id)
        return user and user.is_admin and {"admin": user, "session": session}
