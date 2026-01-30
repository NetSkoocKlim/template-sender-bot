import typing

from sqlalchemy import Integer, Text, Boolean, VARCHAR, BigInteger
from sqlalchemy.orm import mapped_column, Mapped, relationship

from database.models.base import BaseModel

if typing.TYPE_CHECKING:
    from .template import Template

class User(BaseModel):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[str] = mapped_column(VARCHAR(255), unique=True)

    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")
    is_admin: Mapped[bool] = mapped_column(default=False, server_default="false")

    templates: Mapped[list["Template"]] = relationship(back_populates="creator")