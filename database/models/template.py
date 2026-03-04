import datetime
import typing
import typing as t

from sqlalchemy import Column, Text, DateTime, func, TIMESTAMP, ForeignKey, BigInteger, Boolean, select
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseModel, T
from sqlalchemy.types import VARCHAR, TEXT, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship


if typing.TYPE_CHECKING:
    from .user import User

class Template(BaseModel):
    __tablename__ = 'templates'
    # _must_be_active = True

    name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    formated_description: Mapped[str] = mapped_column(Text, nullable=False)
    creator_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_chosen_for_mailing: Mapped[bool] = mapped_column(Boolean, nullable=True, default=False)

    creator: Mapped["User"] = relationship(back_populates="templates")


    @classmethod
    async def update(
            cls: t.Type["Template"],
            session: AsyncSession,
            primary_key: int,
            **kwargs,
    ) -> t.Any["Template", None]:
        instance = await session.get(cls, primary_key)
        if instance and instance.is_active:
            for key, value in kwargs.items():
                setattr(instance, key, value)
            return instance
        return None
