
from sqlalchemy import BigInteger, ForeignKey, VARCHAR, func, select, DateTime, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from datetime import datetime
from database.models import BaseModel


class Receiver(BaseModel):
    __tablename__ = "receivers"

    admin_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    username: Mapped[str] = mapped_column(VARCHAR(255), nullable=False, unique=True,)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


    @classmethod
    def _build_instances(
            cls,
            usernames: list[str],
            admin_id: int,
    ) -> list["Receiver"]:
        instances = []
        for username in usernames:
            instance = {
                "admin_id": admin_id,
                "username": username,
            }
            instances.append(cls(**instance))
        return instances

    @classmethod
    async def add_receivers(
            cls,
            session: AsyncSession,
            usernames: list[str],
            admin_id: int,
    ) -> int:
        if not usernames:
            return 0
        data_to_insert = [
            {"admin_id": admin_id, "username": u}
            for u in usernames
        ]
        stmt = insert(cls).values(data_to_insert)
        stmt = stmt.on_conflict_do_nothing(index_elements=['username'])
        sel_stmt = select(func.count()).select_from(
            stmt.returning(cls.username).cte("inserted_rows")
        )
        result = await session.execute(sel_stmt)
        added_count = result.scalar_one()
        return added_count



    @classmethod
    async def delete_receivers(
            cls,
            session: AsyncSession,
            usernames: list[str],
            admin_id: int,
    ):
        stmt = delete(cls).where(
            cls.admin_id == admin_id,
            cls.username.in_(usernames)
        )
        del_stmt = select(func.count()).select_from(
            stmt.returning(cls.username).cte("deleted_rows")
        )
        result = await session.execute(del_stmt)
        deleted_count = result.scalar_one()
        return deleted_count




