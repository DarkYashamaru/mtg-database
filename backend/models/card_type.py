from datetime import date
from typing import TYPE_CHECKING
from sqlalchemy import Integer, Boolean, Date, Float, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.card import Card
from database.base import Base


class Card_Supertypes(Base):
    __tablename__ = "card_supertypes"

    card_id: Mapped[str] = mapped_column(ForeignKey("cards.oracle_id"), primary_key=True,)
    type_id: Mapped[str] = mapped_column(ForeignKey("supertypes.value"), primary_key=True,)

    card: Mapped["Card"] = relationship(back_populates="supertypes")
    type: Mapped["Supertype"] = relationship(back_populates="card_type")

class Card_Types(Base):
    __tablename__ = "card_card_types"

    card_id: Mapped[str] = mapped_column(ForeignKey("cards.oracle_id"), primary_key=True,)
    type_id: Mapped[str] = mapped_column(ForeignKey("card_types.value"), primary_key=True,)

    card: Mapped["Card"] = relationship(back_populates="types")
    type: Mapped["CardType"] = relationship(back_populates="card_type")

class Card_Subtypes(Base):
    __tablename__ = "card_subtypes"

    card_id: Mapped[str] = mapped_column(ForeignKey("cards.oracle_id"), primary_key=True,)
    type_id: Mapped[str] = mapped_column(ForeignKey("subtypes.value"), primary_key=True,)

    card: Mapped["Card"] = relationship(back_populates="subtypes")
    type: Mapped["Subtype"] = relationship(back_populates="card_type")