from __future__ import annotations

from models.card import Card
from services.marker_support.card_logic import has_self_etb_trigger, is_permanent

MARKER_ID = "self-etb"
MARKER_NAME = "self-etb"
MARKER_DESCRIPTION = "Permanents with triggered abilities caused by their own entry onto the battlefield."


def matches(card: Card) -> bool:
    return is_permanent(card) and has_self_etb_trigger(card)
