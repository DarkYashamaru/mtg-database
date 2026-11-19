from __future__ import annotations

from typing import Any


CLASSIFIER_SCHEMA_VERSION = 1
DECKBUILDER_NAMESPACE = "deckbuilder"
CANTRIP_TAG_ID = "42313c19-8be2-47d9-9d3a-99c39725b87d"


def classify_card_metadata(card: dict[str, Any]) -> dict[str, Any]:
    classifications: dict[str, Any] = {}
    labels: list[str] = []

    cantrip = classify_cantrip(card)
    classifications["cantrip"] = cantrip
    if cantrip["matched"]:
        labels.append("cantrip")

    return {
        "schema_version": CLASSIFIER_SCHEMA_VERSION,
        DECKBUILDER_NAMESPACE: {
            "labels": labels,
            "classifications": classifications,
        },
    }


def classify_cantrip(card: dict[str, Any]) -> dict[str, Any]:
    tag_ids = set(card.get("tag_ids", []))
    matched = CANTRIP_TAG_ID in tag_ids

    return {
        "matched": matched,
        "source": "tag",
        "tag_id": CANTRIP_TAG_ID if matched else None,
        "reason_codes": ["tag_present"] if matched else [],
    }
