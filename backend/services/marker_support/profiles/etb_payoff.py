from __future__ import annotations

from models.card import Card
from services.marker_support.card_logic import has_etb_payoff, is_permanent

MARKER_ID = "etb-payoff"
MARKER_NAME = "etb-payoff"
MARKER_DESCRIPTION = "Permanents with triggered abilities that reward other permanents entering the battlefield."


def matches(card: Card) -> bool:
    return is_permanent(card) and has_etb_payoff(card)
