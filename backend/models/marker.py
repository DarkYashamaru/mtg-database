from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base

if TYPE_CHECKING:
    from models.card import Card


class Marker(Base):
    __tablename__ = "markers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)

    card_markers: Mapped[list["CardMarker"]] = relationship(
        back_populates="marker",
        cascade="all, delete-orphan",
        passive_deletes=True,
        overlaps="cards,markers",
    )

    cards: Mapped[list["Card"]] = relationship(
        "Card",
        secondary="card_markers",
        back_populates="markers",
        viewonly=True,
        overlaps="card_markers,card",
    )

    def __repr__(self) -> str:
        return f"Marker(id={self.id!r}, name={self.name!r})"


class CardMarker(Base):
    __tablename__ = "card_markers"

    marker_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("markers.id", ondelete="CASCADE"),
        primary_key=True,
    )
    oracle_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("cards.oracle_id", ondelete="CASCADE"),
        primary_key=True,
    )

    marker: Mapped["Marker"] = relationship(
        back_populates="card_markers",
        overlaps="cards,markers",
    )
    card: Mapped["Card"] = relationship(
        back_populates="card_markers",
        overlaps="cards,markers",
    )

    def __repr__(self) -> str:
        return f"CardMarker(marker_id={self.marker_id!r}, oracle_id={self.oracle_id!r})"
