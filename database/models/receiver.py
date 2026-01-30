from sqlalchemy import VARCHAR, ForeignKey, Integer
from sqlalchemy.orm import mapped_column, Mapped

from database.models.base import BaseModel

class Receiver(BaseModel):
    __tablename__ = 'receivers'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(VARCHAR(255), ForeignKey('users.username'))
