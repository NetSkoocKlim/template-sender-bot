from .base import BaseModel
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Integer, String


class Admin(BaseModel):
    __tablename__ = 'admins'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str]




