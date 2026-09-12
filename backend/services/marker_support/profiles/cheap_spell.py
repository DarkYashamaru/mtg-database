from __future__ import annotations

from models.card import Card
from services.marker_support.card_logic import is_land

MARKER_ID = "cheap-spell"
MARKER_NAME = "cheap-spell"
MARKER_DESCRIPTION = "Nonland cards with mana value from 0 to 2."


def matches(card: Card) -> bool:
    return 0 <= card.cmc <= 2 and not is_land(card)
