from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base

if TYPE_CHECKING:
    from models.card import Card
    from models.tag import Tag


class Archetype(Base):
    __tablename__ = "archetypes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)

    tags: Mapped[list["Tag"]] = relationship(
        "Tag",
        secondary="archetype_tags",
        back_populates="broad_archetypes",
    )

    cards: Mapped[list["Card"]] = relationship(
        "Card",
        secondary="card_archetypes",
        back_populates="archetypes",
    )


class ArchetypeTag(Base):
    __tablename__ = "archetype_tags"

    archetype_id: Mapped[int] = mapped_column(
        ForeignKey("archetypes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[str] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )


class CardArchetype(Base):
    __tablename__ = "card_archetypes"

    oracle_id: Mapped[str] = mapped_column(
        ForeignKey("cards.oracle_id", ondelete="CASCADE"),
        primary_key=True,
    )
    archetype_id: Mapped[int] = mapped_column(
        ForeignKey("archetypes.id", ondelete="CASCADE"),
        primary_key=True,
    )
