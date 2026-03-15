import datetime


from sqlalchemy import Column, Integer, BigInteger, Text, TIMESTAMP, JSON, ForeignKey, DateTime
from sqlalchemy.dialects.mysql import VARCHAR
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel



class Mailing(BaseModel):
    __tablename__ = "mailings"

    admin_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    template_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("templates.id"))
    started_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )
    finished_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )
    total_requested: Mapped[int] = mapped_column(Integer, nullable=False)
    unresolved_count: Mapped[int] = mapped_column(Integer, nullable=False)
    delivery_failed_count: Mapped[int] = mapped_column(Integer, nullable=False)

    csv_result_key: Mapped[str | None] = mapped_column(VARCHAR(255))

