from __future__ import annotations

from models.card import Card
from services.marker_support.card_logic import has_oracle_text_fragment


MARKER_ID = "tutor-two-basic-lands"
MARKER_NAME = "tutor-two-basic-lands"
MARKER_DESCRIPTION = "Cards whose Oracle text searches for up to two basic land cards."

_ORACLE_TEXT_FRAGMENT = "Search your library for up to two basic land cards"


def matches(card: Card) -> bool:
    return has_oracle_text_fragment(card, _ORACLE_TEXT_FRAGMENT)
