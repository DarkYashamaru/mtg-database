from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.card import Card


def resolve_decklist_cards(
    names: list[str], db: Session, load_options: tuple = ()
) -> tuple[list[tuple[str, Card]], list[str]]:
    exact_cards = db.execute(
        select(Card)
        .options(*load_options)
        .where(Card.name.in_(names))
    ).scalars().all()
    cards_by_name = {card.name: card for card in exact_cards}

    resolved_cards = []
    warnings = []

    for name in names:
        exact_card = cards_by_name.get(name)
        if exact_card is not None:
            resolved_cards.append((name, exact_card))
            continue

        face_prefix = f"{name} // "
        candidates = db.execute(
            select(Card)
            .options(*load_options)
            .where(func.substr(Card.name, 1, len(face_prefix)) == face_prefix)
            .order_by(Card.name)
        ).scalars().all()

        if len(candidates) == 1:
            card = candidates[0]
            resolved_cards.append((name, card))
            warnings.append(f'Resolved "{name}" as "{card.name}".')
        elif not candidates:
            warnings.append(f'Skipped "{name}": no card found.')
        else:
            candidate_names = "; ".join(card.name for card in candidates)
            warnings.append(
                f'Skipped "{name}": multiple cards matched ({candidate_names}).'
            )

    return resolved_cards, warnings
