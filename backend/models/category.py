from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base

if TYPE_CHECKING:
    from models.card import Card
    from models.tag import Tag


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)

    tags: Mapped[list["Tag"]] = relationship(
        "Tag",
        secondary="category_tags",
        back_populates="broad_categories",
    )

    cards: Mapped[list["Card"]] = relationship(
        "Card",
        secondary="card_categories",
        back_populates="categories",
    )


class CategoryTag(Base):
    __tablename__ = "category_tags"

    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[str] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )


class CardCategory(Base):
    __tablename__ = "card_categories"

    oracle_id: Mapped[str] = mapped_column(
        ForeignKey("cards.oracle_id", ondelete="CASCADE"),
        primary_key=True,
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"),
        primary_key=True,
    )
