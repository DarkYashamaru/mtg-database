from __future__ import annotations

from models.card import Card
from services.marker_support.card_logic import has_self_etb_trigger, is_artifact

MARKER_ID = "self-etb-artifact"
MARKER_NAME = "self-etb-artifact"
MARKER_DESCRIPTION = "Artifacts with triggered abilities caused by their own entry onto the battlefield."


def matches(card: Card) -> bool:
    return is_artifact(card) and has_self_etb_trigger(card)
