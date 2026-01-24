from sqlalchemy import VARCHAR
from sqlalchemy.orm import mapped_column, Mapped

from database.models.base import BaseModel


class Receiver(BaseModel):
    __tablename__ = 'receivers'

    username: Mapped[str] = mapped_column(VARCHAR(30), primary_key=True)
