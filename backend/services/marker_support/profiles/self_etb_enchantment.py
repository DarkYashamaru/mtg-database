from __future__ import annotations

from models.card import Card
from services.marker_support.card_logic import has_self_etb_trigger, is_enchantment

MARKER_ID = "self-etb-enchantment"
MARKER_NAME = "self-etb-enchantment"
MARKER_DESCRIPTION = "Enchantments with triggered abilities caused by their own entry onto the battlefield."


def matches(card: Card) -> bool:
    return is_enchantment(card) and has_self_etb_trigger(card)
