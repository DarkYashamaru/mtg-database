from datetime import date
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, Date, Float, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base

if TYPE_CHECKING:
    from models.tag import Tagging


class Card(Base):
    """A unique MTG game object plus its front-face summary fields."""

    __tablename__ = "cards"

    oracle_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    mana_cost: Mapped[str | None] = mapped_column(String(100))
    cmc: Mapped[float] = mapped_column(Float, nullable=False)
    oracle_text: Mapped[str | None] = mapped_column(Text)
    layout: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    power: Mapped[int | None] = mapped_column(String(20))
    toughness: Mapped[int | None] = mapped_column(String(20))
    type_line: Mapped[str] = mapped_column(String(255))
    commander_legal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    standard_legal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    released_at: Mapped[date | None] = mapped_column(Date, index=True)
    
    taggings: Mapped[list["Tagging"]] = relationship(back_populates="card", cascade="all, delete-orphan", passive_deletes=True)

    def __repr__(self) -> str:
        return f"Card(oracle_id={self.oracle_id!r}, name={self.name!r})"
