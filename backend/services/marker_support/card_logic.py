from __future__ import annotations

import re

from models.card import Card


_ETB_TRIGGER_RE = re.compile(
    r"\b(?:when|whenever)\s+"
    r"(?P<subject>[^\n;]{1,240}?)"
    r"\s+enters?"
    r"(?:\s+the battlefield)?\b",
    re.IGNORECASE,
)
_NON_LAND_PERMANENT_TYPE_RE = re.compile(r"\b(?:artifact|battle|creature|enchantment|planeswalker)\b", re.IGNORECASE)
_PERMANENT_TYPE_RE = re.compile(r"\b(?:artifact|battle|creature|enchantment|land|planeswalker)\b", re.IGNORECASE)
_LAND_TYPE_RE = re.compile(r"\bland\b", re.IGNORECASE)
_CREATURE_TYPE_RE = re.compile(r"\bcreature\b", re.IGNORECASE)
_ARTIFACT_TYPE_RE = re.compile(r"\bartifact\b", re.IGNORECASE)
_ENCHANTMENT_TYPE_RE = re.compile(r"\benchantment\b", re.IGNORECASE)


def is_permanent(card: Card) -> bool:
    return any(_PERMANENT_TYPE_RE.search(face.type_line or "") for face in card.faces)

def is_non_land_permanent(card: Card) -> bool:
    return any(_NON_LAND_PERMANENT_TYPE_RE.search(face.type_line or "") for face in card.faces)

def is_land(card: Card) -> bool:
    return any(_LAND_TYPE_RE.search(face.type_line or "") for face in card.faces)

def is_creature(card: Card) -> bool:
    return any(_CREATURE_TYPE_RE.search(face.type_line or "") for face in card.faces)

def is_artifact(card: Card) -> bool:
    return any(_ARTIFACT_TYPE_RE.search(face.type_line or "") for face in card.faces)

def is_enchantment(card: Card) -> bool:
    return any(_ENCHANTMENT_TYPE_RE.search(face.type_line or "") for face in card.faces)


def etb_trigger_subjects(card: Card) -> tuple[str, ...]:
    return tuple(
        match.group("subject").strip()
        for face in card.faces
        for match in _ETB_TRIGGER_RE.finditer(face.oracle_text or "")
    )


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())


def has_oracle_text_fragment(card: Card, fragment: str) -> bool:
    normalized_fragment = _normalize(fragment)
    return bool(normalized_fragment) and any(
        normalized_fragment in _normalize(face.oracle_text or "")
        for face in card.faces
    )


def _self_names(card: Card) -> frozenset[str]:
    names: set[str] = set()
    for raw_name in (card.name, *(face.name for face in card.faces)):
        for part in (raw_name or "").split(" // "):
            part = part.strip()
            if not part:
                continue
            names.add(_normalize(part))
            if "," in part:
                names.add(_normalize(part.split(",", 1)[0]))
    return frozenset(names)


def _subject_includes_self(subject: str, self_names: frozenset[str]) -> bool:
    normalized = _normalize(subject)
    if normalized.startswith("this "):
        return "." not in normalized and ";" not in normalized
    for name in self_names:
        if normalized == name:
            return True
        for connector in (" or ", " and "):
            if normalized.startswith(f"{name}{connector}"):
                remainder = normalized[len(name) + len(connector):]
                if "." not in remainder and ";" not in remainder:
                    return True
    return False


def _subject_includes_other(subject: str, self_names: frozenset[str]) -> bool:
    normalized = _normalize(subject)
    if normalized.startswith("this "):
        return bool(re.search(
            r"\b(?:or|and)\s+(?:an?|one or more\s+)?other\b"
            r"|\b(?:or|and)\s+another\b",
            normalized,
        ))
    for name in self_names:
        if normalized == name:
            return False
        if normalized.startswith(f"{name} or ") or normalized.startswith(f"{name} and "):
            return True
    return True


def has_self_etb_trigger(card: Card) -> bool:
    self_names = _self_names(card)
    return any(_subject_includes_self(subject, self_names) for subject in etb_trigger_subjects(card))


def has_etb_payoff(card: Card) -> bool:
    self_names = _self_names(card)
    return any(_subject_includes_other(subject, self_names) for subject in etb_trigger_subjects(card))
