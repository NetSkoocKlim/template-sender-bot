import datetime
import typing

from sqlalchemy import Column, Text, DateTime, func, TIMESTAMP, ForeignKey, BigInteger

from .base import BaseModel
from sqlalchemy.types import VARCHAR, TEXT, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship


if typing.TYPE_CHECKING:
    from .user import User

class Template(BaseModel):
    __tablename__ = 'templates'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    formated_description: Mapped[str] = mapped_column(Text, nullable=False)
    creator_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP,
                                                          server_default=func.now(),
                                                          )


    creator: Mapped["User"] = relationship(back_populates="templates")

