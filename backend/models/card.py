from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    Float,
    String,
    Text,
    ForeignKey,
    ForeignKeyConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base

if TYPE_CHECKING:
    from models.tag import Tagging
    from models.catalogs import Supertype, CardType, Subtype


class Card(Base):
    """A unique MTG game object."""

    __tablename__ = "cards"

    oracle_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cmc: Mapped[float] = mapped_column(Float, nullable=False)
    layout: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    commander_legal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True,)
    standard_legal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True,)
    released_at: Mapped[date | None] = mapped_column(Date, index=True)

    taggings: Mapped[list["Tagging"]] = relationship(
        back_populates="card",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    color_identity: Mapped[list["Color_Identity"]] = relationship(
        back_populates="card",
        cascade="all, delete-orphan",
    )

    faces: Mapped[list["Card_Face"]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan",
    )

    keywords: Mapped[list["Card_Keyword"]] = relationship(
        back_populates="card",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"Card(oracle_id={self.oracle_id!r}, name={self.name!r})"
    
class Card_Keyword(Base):
    __tablename__ = "card_keyword"

    card_id: Mapped[str] = mapped_column(ForeignKey("cards.oracle_id"), primary_key=True,)
    keyword_value: Mapped[str] = mapped_column(ForeignKey("keywords.value"), primary_key=True,)

    card: Mapped["Card"] = relationship(
        back_populates="keywords"
    )

    keyword: Mapped["Keyword"] = relationship(
        back_populates="card_keyword"
    )


class Card_Face(Base):
    """Represents an individual face of a card."""

    __tablename__ = "card_faces"

    parent_id: Mapped[str] = mapped_column(
        ForeignKey("cards.oracle_id"),
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
    )

    mana_cost: Mapped[str | None] = mapped_column(String(100))
    cmc: Mapped[float] = mapped_column(Float, nullable=False)
    oracle_text: Mapped[str | None] = mapped_column(Text)
    power: Mapped[str | None] = mapped_column(String(20))
    toughness: Mapped[str | None] = mapped_column(String(20))
    type_line: Mapped[str] = mapped_column(String(255))

    small_image: Mapped[str | None] = mapped_column(String(255))
    normal_image: Mapped[str | None] = mapped_column(String(255))
    large_image: Mapped[str | None] = mapped_column(String(255))

    parent: Mapped["Card"] = relationship(
        back_populates="faces"
    )

    supertypes: Mapped[list["Face_Supertypes"]] = relationship(
        back_populates="face",
        cascade="all, delete-orphan",
    )

    types: Mapped[list["Face_Types"]] = relationship(
        back_populates="face",
        cascade="all, delete-orphan",
    )

    subtypes: Mapped[list["Face_Subtypes"]] = relationship(
        back_populates="face",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"Card_Face("
            f"parent_id={self.parent_id!r}, "
            f"name={self.name!r})"
        )


class Face_Supertypes(Base):
    __tablename__ = "face_supertypes"

    card_id: Mapped[str] = mapped_column(primary_key=True)
    face_name: Mapped[str] = mapped_column(primary_key=True)

    type_id: Mapped[str] = mapped_column(
        ForeignKey("supertypes.value"),
        primary_key=True,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["card_id", "face_name"],
            ["card_faces.parent_id", "card_faces.name"],
        ),
    )

    face: Mapped["Card_Face"] = relationship(
        back_populates="supertypes"
    )

    type: Mapped["Supertype"] = relationship(
        back_populates="card_type"
    )


class Face_Types(Base):
    __tablename__ = "face_card_types"

    card_id: Mapped[str] = mapped_column(primary_key=True)
    face_name: Mapped[str] = mapped_column(primary_key=True)

    type_id: Mapped[str] = mapped_column(
        ForeignKey("card_types.value"),
        primary_key=True,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["card_id", "face_name"],
            ["card_faces.parent_id", "card_faces.name"],
        ),
    )

    face: Mapped["Card_Face"] = relationship(
        back_populates="types"
    )

    type: Mapped["CardType"] = relationship(
        back_populates="card_type"
    )


class Face_Subtypes(Base):
    __tablename__ = "face_subtypes"

    card_id: Mapped[str] = mapped_column(primary_key=True)
    face_name: Mapped[str] = mapped_column(primary_key=True)

    type_id: Mapped[str] = mapped_column(
        ForeignKey("subtypes.value"),
        primary_key=True,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["card_id", "face_name"],
            ["card_faces.parent_id", "card_faces.name"],
        ),
    )

    face: Mapped["Card_Face"] = relationship(
        back_populates="subtypes"
    )

    type: Mapped["Subtype"] = relationship(
        back_populates="card_type"
    )


class Card_Type_Collection:
    super_types: list[Face_Supertypes]
    card_types: list[Face_Types]
    sub_types: list[Face_Subtypes]

    def __init__(self):
        self.super_types: list[Face_Supertypes] = []
        self.card_types: list[Face_Types] = []
        self.sub_types: list[Face_Subtypes] = []