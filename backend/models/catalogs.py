# models/catalogs.py
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.card_type import Card_Supertypes, Card_Types, Card_Subtypes
from database.base import Base


class CatalogBase(Base):
    __abstract__ = True

    value: Mapped[str] = mapped_column(String(255), primary_key=True, nullable=False, unique=True, index=True)


class Supertype(CatalogBase):
    __tablename__ = "supertypes"

    card_type: Mapped[list["Card_Supertypes"]] = relationship(
        back_populates="type"
    )


class CardType(CatalogBase):
    __tablename__ = "card_types"

    card_type: Mapped[list["Card_Types"]] = relationship(
        back_populates="type"
    )

class Subtype(CatalogBase):
    __tablename__ = "subtypes"

    card_type: Mapped[list["Card_Subtypes"]] = relationship(
        back_populates="type"
    )

class ArtifactType(CatalogBase):
    __tablename__ = "artifact_types"


class BattleType(CatalogBase):
    __tablename__ = "battle_types"


class CreatureType(CatalogBase):
    __tablename__ = "creature_types"


class EnchantmentType(CatalogBase):
    __tablename__ = "enchantment_types"


class LandType(CatalogBase):
    __tablename__ = "land_types"


class PlaneswalkerType(CatalogBase):
    __tablename__ = "planeswalker_types"


class SpellType(CatalogBase):
    __tablename__ = "spell_types"


class Power(CatalogBase):
    __tablename__ = "powers"


class Toughness(CatalogBase):
    __tablename__ = "toughnesses"


class Loyalty(CatalogBase):
    __tablename__ = "loyalties"


class KeywordAbility(CatalogBase):
    __tablename__ = "keyword_abilities"


class KeywordAction(CatalogBase):
    __tablename__ = "keyword_actions"


class AbilityWord(CatalogBase):
    __tablename__ = "ability_words"