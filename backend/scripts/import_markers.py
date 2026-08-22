from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import delete, exists, select

from database.session import session_scope
from models.card import Card, Card_Face
from models.marker import CardMarker, Marker


CHEAP_SPELL_MARKER_ID = "cheap-spell"
CHEAP_SPELL_MARKER_NAME = "cheap-spell"
CHEAP_SPELL_MARKER_DESCRIPTION = "Cards with mana value from 0 to 2."


def import_markers() -> int:
    with session_scope() as session:
        inserted = 0

        inserted += sync_cheap_spell_marker(session)

        session.commit()
        return inserted


def sync_cheap_spell_marker(session) -> int:
    marker = session.get(Marker, CHEAP_SPELL_MARKER_ID)

    if marker is None:
        marker = Marker(
            id=CHEAP_SPELL_MARKER_ID,
            name=CHEAP_SPELL_MARKER_NAME,
            description=CHEAP_SPELL_MARKER_DESCRIPTION,
        )
        session.add(marker)
    else:
        marker.name = CHEAP_SPELL_MARKER_NAME
        marker.description = CHEAP_SPELL_MARKER_DESCRIPTION

    matching_oracle_ids = session.scalars(
        select(Card.oracle_id).where(
            Card.cmc >= 0,
            Card.cmc <= 2,
            ~exists(
                select(1)
                .select_from(Card_Face)
                .where(
                    Card_Face.parent_id == Card.oracle_id,
                    Card_Face.type_line.ilike("%Land%"),
                )
            ),
        )
    ).all()

    return sync_marker_membership(
        session,
        marker_id=CHEAP_SPELL_MARKER_ID,
        oracle_ids=matching_oracle_ids,
    )


def sync_marker_membership(
    session,
    *,
    marker_id: str,
    oracle_ids: Iterable[str],
) -> int:
    desired_oracle_ids = set(oracle_ids)

    existing_oracle_ids = set(
        session.scalars(
            select(CardMarker.oracle_id).where(CardMarker.marker_id == marker_id)
        ).all()
    )

    to_insert = desired_oracle_ids - existing_oracle_ids
    to_delete = existing_oracle_ids - desired_oracle_ids

    if to_delete:
        session.execute(
            delete(CardMarker).where(
                CardMarker.marker_id == marker_id,
                CardMarker.oracle_id.in_(to_delete),
            )
        )

    for oracle_id in to_insert:
        session.add(CardMarker(marker_id=marker_id, oracle_id=oracle_id))

    return len(to_insert)
