from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Float, ForeignKey, ForeignKeyConstraint, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base

if TYPE_CHECKING:
    from models.card import Card


class CardPrinting(Base):
    """One Scryfall Default Cards record, keyed by Scryfall's printing UUID."""

    __tablename__ = "card_printings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    oracle_id: Mapped[str | None] = mapped_column(ForeignKey("cards.oracle_id"), index=True)
    arena_id: Mapped[int | None] = mapped_column(Integer)
    lang: Mapped[str] = mapped_column(String(16), index=True)
    mtgo_id: Mapped[int | None] = mapped_column(Integer)
    mtgo_foil_id: Mapped[int | None] = mapped_column(Integer)
    resource_id: Mapped[str | None] = mapped_column(String(255))
    tcgplayer_id: Mapped[int | None] = mapped_column(Integer)
    tcgplayer_etched_id: Mapped[int | None] = mapped_column(Integer)
    cardmarket_id: Mapped[int | None] = mapped_column(Integer)
    object: Mapped[str] = mapped_column(String(32))
    layout: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    cmc: Mapped[float] = mapped_column(Float)
    color_identity_text: Mapped[str] = mapped_column(String(16), default="")
    defense: Mapped[str | None] = mapped_column(String(32))
    edhrec_rank: Mapped[int | None] = mapped_column(Integer)
    game_changer: Mapped[bool | None] = mapped_column(Boolean)
    hand_modifier: Mapped[str | None] = mapped_column(String(32))
    life_modifier: Mapped[str | None] = mapped_column(String(32))
    loyalty: Mapped[str | None] = mapped_column(String(32))
    mana_cost: Mapped[str | None] = mapped_column(String(255))
    oracle_text: Mapped[str | None] = mapped_column(Text)
    penny_rank: Mapped[int | None] = mapped_column(Integer)
    power: Mapped[str | None] = mapped_column(String(32))
    reserved: Mapped[bool] = mapped_column(Boolean, default=False)
    toughness: Mapped[str | None] = mapped_column(String(32))
    type_line: Mapped[str | None] = mapped_column(String(255))
    artist: Mapped[str | None] = mapped_column(String(255))
    booster: Mapped[bool] = mapped_column(Boolean, default=False)
    border_color: Mapped[str] = mapped_column(String(32))
    card_back_id: Mapped[str | None] = mapped_column(String(36))
    collector_number: Mapped[str] = mapped_column(String(64), index=True)
    content_warning: Mapped[bool | None] = mapped_column(Boolean)
    digital: Mapped[bool] = mapped_column(Boolean, default=False)
    flavor_name: Mapped[str | None] = mapped_column(String(255))
    flavor_text: Mapped[str | None] = mapped_column(Text)
    frame: Mapped[str] = mapped_column(String(32))
    full_art: Mapped[bool] = mapped_column(Boolean, default=False)
    highres_image: Mapped[bool] = mapped_column(Boolean, default=False)
    illustration_id: Mapped[str | None] = mapped_column(String(36), index=True)
    image_status: Mapped[str] = mapped_column(String(32))
    oversized: Mapped[bool] = mapped_column(Boolean, default=False)
    printed_name: Mapped[str | None] = mapped_column(String(255))
    printed_text: Mapped[str | None] = mapped_column(Text)
    printed_type_line: Mapped[str | None] = mapped_column(String(255))
    promo: Mapped[bool] = mapped_column(Boolean, default=False)
    rarity: Mapped[str] = mapped_column(String(32))
    released_at: Mapped[date | None] = mapped_column(Date, index=True)
    reprint: Mapped[bool] = mapped_column(Boolean, default=False)
    set_code: Mapped[str] = mapped_column("set", String(16), index=True)
    set_id: Mapped[str] = mapped_column(String(36), index=True)
    set_name: Mapped[str] = mapped_column(String(255))
    set_type: Mapped[str] = mapped_column(String(64))
    story_spotlight: Mapped[bool] = mapped_column(Boolean, default=False)
    textless: Mapped[bool] = mapped_column(Boolean, default=False)
    variation: Mapped[bool] = mapped_column(Boolean, default=False)
    variation_of: Mapped[str | None] = mapped_column(String(36))
    security_stamp: Mapped[str | None] = mapped_column(String(32))
    watermark: Mapped[str | None] = mapped_column(String(255))
    previewed_at: Mapped[date | None] = mapped_column(Date)
    preview_source: Mapped[str | None] = mapped_column(String(255))
    preview_source_uri: Mapped[str | None] = mapped_column(Text)

    card: Mapped["Card | None"] = relationship(back_populates="printings")
    faces: Mapped[list["PrintingFace"]] = relationship(back_populates="printing", cascade="all, delete-orphan")
    values: Mapped[list["PrintingValue"]] = relationship(back_populates="printing", cascade="all, delete-orphan")
    uris: Mapped[list["PrintingUri"]] = relationship(back_populates="printing", cascade="all, delete-orphan")
    legalities: Mapped[list["PrintingLegality"]] = relationship(back_populates="printing", cascade="all, delete-orphan")
    parts: Mapped[list["PrintingPart"]] = relationship(back_populates="printing", cascade="all, delete-orphan")


class PrintingFace(Base):
    __tablename__ = "printing_faces"

    printing_id: Mapped[str] = mapped_column(ForeignKey("card_printings.id", ondelete="CASCADE"), primary_key=True)
    face_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    artist: Mapped[str | None] = mapped_column(String(255))
    artist_id: Mapped[str | None] = mapped_column(String(36))
    cmc: Mapped[float | None] = mapped_column(Float)
    color_indicator_text: Mapped[str] = mapped_column(String(16), default="")
    colors_text: Mapped[str] = mapped_column(String(16), default="")
    defense: Mapped[str | None] = mapped_column(String(32))
    flavor_text: Mapped[str | None] = mapped_column(Text)
    illustration_id: Mapped[str | None] = mapped_column(String(36))
    layout: Mapped[str | None] = mapped_column(String(64))
    loyalty: Mapped[str | None] = mapped_column(String(32))
    mana_cost: Mapped[str | None] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    object: Mapped[str] = mapped_column(String(32))
    oracle_id: Mapped[str | None] = mapped_column(String(36))
    oracle_text: Mapped[str | None] = mapped_column(Text)
    power: Mapped[str | None] = mapped_column(String(32))
    printed_name: Mapped[str | None] = mapped_column(String(255))
    printed_text: Mapped[str | None] = mapped_column(Text)
    printed_type_line: Mapped[str | None] = mapped_column(String(255))
    toughness: Mapped[str | None] = mapped_column(String(32))
    type_line: Mapped[str | None] = mapped_column(String(255))
    watermark: Mapped[str | None] = mapped_column(String(255))

    printing: Mapped["CardPrinting"] = relationship(back_populates="faces")
    uris: Mapped[list["PrintingFaceUri"]] = relationship(back_populates="face", cascade="all, delete-orphan")


class PrintingValue(Base):
    """A normalized scalar-array member (keywords, finishes, games, artists, etc.)."""
    __tablename__ = "printing_values"
    printing_id: Mapped[str] = mapped_column(ForeignKey("card_printings.id", ondelete="CASCADE"), primary_key=True)
    field: Mapped[str] = mapped_column(String(64), primary_key=True)
    # Scryfall arrays may intentionally contain the same value more than once.
    # Position preserves both those occurrences and the source ordering.
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    value: Mapped[str] = mapped_column(String(255))
    printing: Mapped["CardPrinting"] = relationship(back_populates="values")


class PrintingUri(Base):
    __tablename__ = "printing_uris"
    printing_id: Mapped[str] = mapped_column(ForeignKey("card_printings.id", ondelete="CASCADE"), primary_key=True)
    group: Mapped[str] = mapped_column(String(32), primary_key=True)
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    uri: Mapped[str] = mapped_column(Text)
    printing: Mapped["CardPrinting"] = relationship(back_populates="uris")


class PrintingFaceUri(Base):
    __tablename__ = "printing_face_uris"
    printing_id: Mapped[str] = mapped_column(primary_key=True)
    face_index: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    uri: Mapped[str] = mapped_column(Text)
    __table_args__ = (
        ForeignKeyConstraint(
            ["printing_id", "face_index"],
            ["printing_faces.printing_id", "printing_faces.face_index"],
            ondelete="CASCADE",
        ),
    )
    face: Mapped["PrintingFace"] = relationship(back_populates="uris")


class PrintingLegality(Base):
    __tablename__ = "printing_legalities"
    printing_id: Mapped[str] = mapped_column(ForeignKey("card_printings.id", ondelete="CASCADE"), primary_key=True)
    format: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(32))
    printing: Mapped["CardPrinting"] = relationship(back_populates="legalities")


class PrintingPart(Base):
    __tablename__ = "printing_parts"
    printing_id: Mapped[str] = mapped_column(ForeignKey("card_printings.id", ondelete="CASCADE"), primary_key=True)
    related_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    component: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    type_line: Mapped[str] = mapped_column(String(255))
    uri: Mapped[str] = mapped_column(Text)
    printing: Mapped["CardPrinting"] = relationship(back_populates="parts")
