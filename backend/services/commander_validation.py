from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from models.card import Card


@dataclass(frozen=True)
class CommanderValidationResult:
    oracle_ids: list[str]
    valid: bool
    code: str
    message: str


def _values(entries) -> set[str]:
    return {
        entry.type.value.casefold()
        for entry in entries
        if getattr(entry, "type", None) is not None and getattr(entry.type, "value", None)
    }


def _texts(card: Card) -> str:
    return "\n".join(face.oracle_text or "" for face in card.faces).casefold()


def _keywords(card: Card) -> set[str]:
    return {
        entry.keyword.value.casefold()
        for entry in card.keywords
        if getattr(entry, "keyword", None) is not None and entry.keyword.value
    }


def _is_legendary_creature(card: Card) -> bool:
    return any(
        "legendary" in _values(face.supertypes) and "creature" in _values(face.types)
        for face in card.faces
    )


def _is_background(card: Card) -> bool:
    return any("background" in _values(face.subtypes) for face in card.faces)


def _is_time_lord_doctor(card: Card) -> bool:
    return any({"time lord", "doctor"} <= _values(face.subtypes) for face in card.faces)


def _can_be_commander(card: Card) -> bool:
    return card.commander_legal and (
        _is_legendary_creature(card) or "can be your commander" in _texts(card)
    )


def _has_keyword_or_text(card: Card, value: str) -> bool:
    return value in _keywords(card) or value in _texts(card)


def _partner_with_name(card: Card) -> str | None:
    match = re.search(r"partner with\s+(.+?)(?:\s*\(|\n|$)", _texts(card))
    return match.group(1).strip().casefold() if match else None


def validate_commander_selection(
    cards_by_oracle_id: Mapping[str, Card],
    oracle_ids: Sequence[str],
) -> CommanderValidationResult:
    ids = list(dict.fromkeys(oracle_ids))
    if len(ids) != len(oracle_ids):
        return CommanderValidationResult(ids, False, "duplicate_commander", "A commander can only appear once.")
    if not ids:
        return CommanderValidationResult(ids, True, "empty", "No commanders selected.")
    if len(ids) > 2:
        return CommanderValidationResult(ids, False, "too_many_commanders", "A deck can have at most two commanders.")

    cards = [cards_by_oracle_id.get(oracle_id) for oracle_id in ids]
    if any(card is None for card in cards):
        return CommanderValidationResult(ids, False, "unknown_card", "One or more commander cards could not be found.")
    first = cards[0]
    if len(cards) == 1:
        if _can_be_commander(first):
            return CommanderValidationResult(ids, True, "eligible", "This card can be your commander.")
        return CommanderValidationResult(ids, False, "not_eligible", "This card is not eligible to be your commander.")

    second = cards[1]
    if not first.commander_legal or not second.commander_legal:
        return CommanderValidationResult(ids, False, "commander_illegal", "Both commanders must be legal in Commander.")

    if _has_keyword_or_text(first, "friends forever") and _has_keyword_or_text(second, "friends forever"):
        return CommanderValidationResult(ids, True, "friends_forever", "These cards can be paired through Friends forever.")
    first_partner = _partner_with_name(first)
    second_partner = _partner_with_name(second)
    if first_partner == second.name.casefold() and second_partner == first.name.casefold():
        return CommanderValidationResult(ids, True, "partner_with", "These cards are paired by Partner with.")
    if (
        (_has_keyword_or_text(first, "partner") and not first_partner)
        and (_has_keyword_or_text(second, "partner") and not second_partner)
        and _can_be_commander(first) and _can_be_commander(second)
    ):
        return CommanderValidationResult(ids, True, "partner", "These cards can be paired through Partner.")
    if (
        _has_keyword_or_text(first, "choose a background") and _can_be_commander(first) and _is_background(second)
    ) or (
        _has_keyword_or_text(second, "choose a background") and _can_be_commander(second) and _is_background(first)
    ):
        return CommanderValidationResult(ids, True, "choose_a_background", "These cards can be paired through Choose a Background.")
    if (
        _has_keyword_or_text(first, "doctor's companion") and _can_be_commander(first) and _is_time_lord_doctor(second) and _can_be_commander(second)
    ) or (
        _has_keyword_or_text(second, "doctor's companion") and _can_be_commander(second) and _is_time_lord_doctor(first) and _can_be_commander(first)
    ):
        return CommanderValidationResult(ids, True, "doctors_companion", "These cards can be paired through Doctor's companion.")
    return CommanderValidationResult(ids, False, "invalid_pair", "These cards cannot be paired as commanders.")

