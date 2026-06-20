# models/catalogs.py
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.card import Face_Supertypes, Face_Types, Face_Subtypes
from database.base import Base


class CatalogBase(Base):
    __abstract__ = True

    value: Mapped[str] = mapped_column(String(255), primary_key=True, nullable=False, unique=True, index=True)


class Supertype(CatalogBase):
    __tablename__ = "supertypes"

    card_type: Mapped[list["Face_Supertypes"]] = relationship(
        back_populates="type"
    )


class CardType(CatalogBase):
    __tablename__ = "card_types"

    card_type: Mapped[list["Face_Types"]] = relationship(
        back_populates="type"
    )

class Subtype(CatalogBase):
    __tablename__ = "subtypes"

    card_type: Mapped[list["Face_Subtypes"]] = relationship(
        back_populates="type"
    )


class Power(CatalogBase):
    __tablename__ = "powers"


class Toughness(CatalogBase):
    __tablename__ = "toughnesses"


class Loyalty(CatalogBase):
    __tablename__ = "loyalties"

class Keyword(CatalogBase):
    __tablename__ = "keywords"

    card_keyword: Mapped[list["Card_Keyword"]] = relationship(
        back_populates="keyword",
        cascade="all, delete-orphan",
    )