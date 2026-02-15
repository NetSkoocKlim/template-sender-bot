import asyncio
import typing

from sqlalchemy import VARCHAR, BigInteger, text, bindparam, ARRAY, TEXT
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import mapped_column, Mapped, relationship

from database.models.base import BaseModel

if typing.TYPE_CHECKING:
    from .template import Template

class User(BaseModel):
    __tablename__ = 'users'

    username: Mapped[str] = mapped_column(VARCHAR(255), unique=True)

    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")
    is_admin: Mapped[bool] = mapped_column(default=False, server_default="false")

    templates: Mapped[list["Template"]] = relationship(back_populates="creator")


    @classmethod
    async def get_ids_by_usernames(cls, session: AsyncSession, usernames: list[str]) -> list[int]:
        if not usernames:
            return []
        query = text("""
                   SELECT u.username, t.id
                   FROM unnest((:usernames)::text[]) WITH ORDINALITY AS u(username, ord)
                   LEFT JOIN users t USING (username)
                   ORDER BY u.ord;
                   """).bindparams(bindparam("usernames", type_=ARRAY(TEXT)))
        results = await session.execute(query, {"usernames": usernames})
        return [row[1] for row in results.fetchall()]
