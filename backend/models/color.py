from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base

if TYPE_CHECKING:
    from models.card import Card


class Color(Base):
    """This table represents each mana color."""

    __tablename__ = "colors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(1), nullable=False, unique=True)

    color_identity: Mapped[list["Color_Identity"]] = relationship(
        back_populates="color"
    )

    produced_mana: Mapped[list["CardProducedMana"]] = relationship(
        back_populates="color",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"Color(id={self.id!r}, name={self.name!r}, symbol={self.symbol!r})"


class ScryfallSymbol(Base):
    """One object from Scryfall's /symbology endpoint."""
    __tablename__ = "scryfall_symbols"
    symbol: Mapped[str] = mapped_column(String(64), primary_key=True)
    svg_uri: Mapped[str | None] = mapped_column(Text)
    english: Mapped[str] = mapped_column(Text)
    transposable: Mapped[bool] = mapped_column(Boolean, default=False)
    appears_in_mana_costs: Mapped[bool] = mapped_column(Boolean, default=False)
    mana_value: Mapped[float | None] = mapped_column(Float)
    hybrid: Mapped[bool] = mapped_column(Boolean, default=False)
    phyrexian: Mapped[bool] = mapped_column(Boolean, default=False)
    replaces: Mapped[str | None] = mapped_column(String(64))
    funny: Mapped[bool] = mapped_column(Boolean, default=False)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)


class CardProducedManaSymbol(Base):
    """An exact produced_mana value, including non-color symbols such as T."""
    __tablename__ = "card_produced_mana_symbols"
    card_id: Mapped[str] = mapped_column(ForeignKey("cards.oracle_id", ondelete="CASCADE"), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    value: Mapped[str] = mapped_column(String(64))
    card: Mapped["Card"] = relationship(back_populates="produced_mana_symbols")


class CardColor(Base):
    __tablename__ = "card_colors"
    color_id: Mapped[int] = mapped_column(ForeignKey("colors.id"), primary_key=True)
    card_id: Mapped[str] = mapped_column(ForeignKey("cards.oracle_id", ondelete="CASCADE"), primary_key=True)


class CardColorIndicator(Base):
    __tablename__ = "card_color_indicators"
    color_id: Mapped[int] = mapped_column(ForeignKey("colors.id"), primary_key=True)
    card_id: Mapped[str] = mapped_column(ForeignKey("cards.oracle_id", ondelete="CASCADE"), primary_key=True)


class FaceColor(Base):
    __tablename__ = "face_colors"
    card_id: Mapped[str] = mapped_column(primary_key=True)
    face_index: Mapped[int] = mapped_column(primary_key=True)
    color_id: Mapped[int] = mapped_column(ForeignKey("colors.id"), primary_key=True)


class FaceColorIndicator(Base):
    __tablename__ = "face_color_indicators"
    card_id: Mapped[str] = mapped_column(primary_key=True)
    face_index: Mapped[int] = mapped_column(primary_key=True)
    color_id: Mapped[int] = mapped_column(ForeignKey("colors.id"), primary_key=True)


# Legacy derived table retained only for compatibility with existing imports.
class CardProducedMana(Base):

    __tablename__ = "card_produced_mana"

    color_id: Mapped[int] = mapped_column(
        ForeignKey("colors.id", ondelete="CASCADE"),
        primary_key=True,
    )

    card_id: Mapped[str] = mapped_column(
        ForeignKey("cards.oracle_id", ondelete="CASCADE"),
        primary_key=True,
    )

    card: Mapped["Card"] = relationship(back_populates="produced_mana")
    color: Mapped["Color"] = relationship(back_populates="produced_mana")


class Color_Identity(Base):
    __tablename__ = "color_identity"

    color_id: Mapped[int] = mapped_column(
        ForeignKey("colors.id", ondelete="CASCADE"),
        primary_key=True,
    )

    card_id: Mapped[str] = mapped_column(
        ForeignKey("cards.oracle_id", ondelete="CASCADE"),
        primary_key=True,
    )

    card: Mapped["Card"] = relationship(back_populates="color_identity")
    color: Mapped["Color"] = relationship(back_populates="color_identity")
