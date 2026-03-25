import datetime

from sqlalchemy import Integer, BigInteger, VARCHAR, Text, TIMESTAMP, JSON, ForeignKey, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel

import enum

class MailingStatus(enum.IntEnum):
    SAVED = 0
    PENDING = 1
    FAILED = 2


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

    s3_key: Mapped[str | None] = mapped_column(VARCHAR(255))
    save_status: Mapped[MailingStatus] = mapped_column(
        Enum(
            MailingStatus,
            native_enum=False,
            values_callable=lambda enum_cls: [str(item.value) for item in enum_cls],
        ),
        nullable=False,

        server_default=str(MailingStatus.PENDING.value)
    )
