from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base

if TYPE_CHECKING:
    from models.card import Card


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)

    parents: Mapped[list["Tag"]] = relationship(
        "Tag",
        secondary="tag_relations",
        primaryjoin="Tag.id == TagRelation.child_id",
        secondaryjoin="Tag.id == TagRelation.parent_id",
        back_populates="children",
    )

    children: Mapped[list["Tag"]] = relationship(
        "Tag",
        secondary="tag_relations",
        primaryjoin="Tag.id == TagRelation.parent_id",
        secondaryjoin="Tag.id == TagRelation.child_id",
        back_populates="parents",
    )

    taggings: Mapped[list["Tagging"]] = relationship(
        back_populates="tag",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    categories = relationship(
        "ArchetypeCategory",
        secondary="archetype_category_tags",
        back_populates="tags"
    )

    def __repr__(self) -> str:
        return f"Tag(id={self.id!r}, label={self.label!r}, type={self.type!r})"


class TagRelation(Base):
    __tablename__ = "tag_relations"

    parent_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )
    child_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )

    def __repr__(self) -> str:
        return f"TagRelation(parent_id={self.parent_id!r}, child_id={self.child_id!r})"


class Tagging(Base):
    __tablename__ = "taggings"

    tag_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )
    oracle_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("cards.oracle_id", ondelete="CASCADE"),
        primary_key=True,
    )

    # optional note from Scryfall; safe to keep
    annotation: Mapped[str | None] = mapped_column(Text)

    tag: Mapped["Tag"] = relationship(back_populates="taggings")
    card: Mapped["Card"] = relationship(back_populates="taggings")

    def __repr__(self) -> str:
        return f"Tagging(tag_id={self.tag_id!r}, oracle_id={self.oracle_id!r})"