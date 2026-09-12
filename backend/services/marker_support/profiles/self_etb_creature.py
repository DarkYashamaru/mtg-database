from __future__ import annotations

from models.card import Card
from services.marker_support.card_logic import has_self_etb_trigger, is_creature

MARKER_ID = "self-etb-creature"
MARKER_NAME = "self-etb-creature"
MARKER_DESCRIPTION = "Creatures with triggered abilities caused by their own entry onto the battlefield."


def matches(card: Card) -> bool:
    return is_creature(card) and has_self_etb_trigger(card)
