from sqlalchemy import Column, Text


from .base import BaseModel
from sqlalchemy.types import VARCHAR, TEXT, Integer
from sqlalchemy.orm import Mapped, mapped_column


class Template(BaseModel):
    __tablename__ = 'templates'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(VARCHAR(30), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

