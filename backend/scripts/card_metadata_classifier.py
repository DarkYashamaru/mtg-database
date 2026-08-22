from __future__ import annotations

from typing import Any


CLASSIFIER_SCHEMA_VERSION = 1
DECKBUILDER_NAMESPACE = "deckbuilder"


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
    tag_slugs = sorted(set(card.get("tag_slugs", [])))
    matched = "cantrip" in tag_slugs

    return {
        "matched": matched,
        "source": "tag",
        "tag_slug": "cantrip" if matched else None,
        "reason_codes": ["tag_present"] if matched else [],
    }
