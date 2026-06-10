from datetime import date
from typing import TYPE_CHECKING
from sqlalchemy import Integer, Boolean, Date, Float, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.card import Card

from database.base import Base


class Card_Face(Base):
    """Table that represents card faces for card with special layouts like adventure, transform, etc."""

    __tablename__ = "card_faces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    parent_id: Mapped[str] = mapped_column(String(36), ForeignKey("cards.oracle_id"), nullable=False,)
    parent: Mapped["Card"] = relationship()

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    mana_cost: Mapped[str | None] = mapped_column(String(100))
    cmc: Mapped[float] = mapped_column(Float, nullable=False)
    oracle_text: Mapped[str | None] = mapped_column(Text)
    power: Mapped[str | None] = mapped_column(String(20))
    toughness: Mapped[str | None] = mapped_column(String(20))
    type_line: Mapped[str] = mapped_column(String(255))
    
    def __repr__(self) -> str:
        return f"Card(id={self.id!r}, name={self.name!r})"
