from __future__ import annotations

import csv
from dataclasses import dataclass

from sqlalchemy import exists, false, func, or_, select
from sqlalchemy.orm import Session

from models.card import Card, Card_Face
from models.tag import Tag, Tagging


@dataclass(frozen=True)
class TagSearchTerm:
    value: str
    exact: bool


def parse_search_terms(text_list: list[str]) -> list[str]:
    """
    Split comma-separated search terms while preserving double-quoted phrases.
    """
    if not text_list:
        return []

    combined_string = ",".join(text_list)
    reader = csv.reader([combined_string], skipinitialspace=True)

    try:
        return [term.strip() for row in reader for term in row if term.strip()]
    except Exception:
        return [term.strip() for term in text_list if term.strip()]


def card_type_match_clause(card_type: str):
    """Require every comma-separated type term to match one card face."""
    terms = parse_search_terms([card_type])
    if not terms:
        return None
    return exists(
        select(1)
        .select_from(Card_Face)
        .where(
            Card_Face.parent_id == Card.oracle_id,
            *(Card_Face.type_line.ilike(f"%{term}%") for term in terms),
        )
    )


def card_cmc_match_clauses(
    cmc_min: float | None,
    cmc_max: float | None,
) -> tuple:
    """Build inclusive Oracle-level mana value filters."""
    clauses = []
    if (cmc_min is not None and cmc_min < 0) or (cmc_max is not None and cmc_max < 0):
        raise ValueError("CMC bounds must be non-negative")
    if cmc_min is not None and cmc_max is not None and cmc_min > cmc_max:
        raise ValueError("cmc_min cannot be greater than cmc_max")

    if cmc_min is not None:
        clauses.append(Card.cmc >= cmc_min)
    if cmc_max is not None:
        clauses.append(Card.cmc <= cmc_max)
    return tuple(clauses)


def _split_raw_tag_terms(text_list: list[str]) -> list[str]:
    """Split commas outside quotes while retaining quote characters."""
    terms: list[str] = []

    for text in text_list:
        buffer: list[str] = []
        in_quotes = False
        index = 0

        while index < len(text):
            character = text[index]
            if character == '"':
                buffer.append(character)
                if in_quotes and index + 1 < len(text) and text[index + 1] == '"':
                    buffer.append('"')
                    index += 2
                    continue
                in_quotes = not in_quotes
            elif character == "," and not in_quotes:
                term = "".join(buffer).strip()
                if term:
                    terms.append(term)
                buffer = []
            else:
                buffer.append(character)
            index += 1

        term = "".join(buffer).strip()
        if term:
            terms.append(term)

    return terms


def _decode_exact_tag_term(raw_term: str) -> str | None:
    """Decode a fully quoted term, accepting CSV-style doubled quotes."""
    if len(raw_term) < 2 or not raw_term.startswith('"') or not raw_term.endswith('"'):
        return None

    inner = raw_term[1:-1]
    decoded: list[str] = []
    index = 0
    while index < len(inner):
        if inner[index] != '"':
            decoded.append(inner[index])
            index += 1
            continue
        if index + 1 >= len(inner) or inner[index + 1] != '"':
            return None
        decoded.append('"')
        index += 2

    return "".join(decoded).strip()


def parse_tag_search_terms(text_list: list[str]) -> list[TagSearchTerm]:
    """
    Parse tag filters.

    Fully quoted terms are exact matches. Unquoted terms are substring matches.
    Empty terms are ignored, and malformed quotes remain literal search text.
    """
    parsed: list[TagSearchTerm] = []
    for raw_term in _split_raw_tag_terms(text_list):
        exact_value = _decode_exact_tag_term(raw_term)
        if exact_value is not None:
            if exact_value:
                parsed.append(TagSearchTerm(value=exact_value, exact=True))
            continue
        parsed.append(TagSearchTerm(value=raw_term, exact=False))
    return parsed


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def resolve_tag_ids(db: Session, term: TagSearchTerm) -> tuple[str, ...]:
    """Resolve matching catalog tags once before applying them to cards."""
    if term.exact:
        normalized = term.value.lower()
        predicate = or_(
            func.lower(Tag.slug) == normalized,
            func.lower(Tag.label) == normalized,
        )
    else:
        pattern = f"%{_escape_like(term.value)}%"
        predicate = or_(
            Tag.slug.ilike(pattern, escape="\\"),
            Tag.label.ilike(pattern, escape="\\"),
        )

    return tuple(db.scalars(select(Tag.id).where(predicate)))


def card_tag_match_clause(tag_ids: tuple[str, ...]):
    """Match cards directly tagged with any one of the resolved catalog tags."""
    if not tag_ids:
        return false()
    return exists(
        select(1)
        .select_from(Tagging)
        .where(
            Tagging.oracle_id == Card.oracle_id,
            Tagging.tag_id.in_(tag_ids),
        )
    )
