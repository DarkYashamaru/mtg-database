from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.card import Card


def load_cards_by_oracle_ids(
    db: Session,
    raw_oracle_ids: Iterable[str],
    *,
    load_options: tuple = (),
    chunk_size: int = 500,
) -> tuple[list[Card], list[str]]:
    """Return unique cards in first-requested order plus unresolved Oracle IDs."""
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive.")

    oracle_ids: list[str] = []
    seen: set[str] = set()
    for raw_oracle_id in raw_oracle_ids:
        oracle_id = raw_oracle_id.strip()
        if not oracle_id:
            raise ValueError("oracle_ids cannot contain blank values.")
        if oracle_id in seen:
            continue
        seen.add(oracle_id)
        oracle_ids.append(oracle_id)

    cards: list[Card] = []
    for start in range(0, len(oracle_ids), chunk_size):
        chunk = oracle_ids[start:start + chunk_size]
        cards.extend(
            db.execute(
                select(Card)
                .options(*load_options)
                .where(Card.oracle_id.in_(chunk))
            ).scalars().all()
        )

    cards_by_oracle_id = {card.oracle_id: card for card in cards}
    missing_oracle_ids = [
        oracle_id
        for oracle_id in oracle_ids
        if oracle_id not in cards_by_oracle_id
    ]
    return (
        [
            cards_by_oracle_id[oracle_id]
            for oracle_id in oracle_ids
            if oracle_id in cards_by_oracle_id
        ],
        missing_oracle_ids,
    )
