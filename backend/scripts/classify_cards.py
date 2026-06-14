from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(
    0,
    str(ROOT)
)

from database.create_database import create_database
from services.ai.classification.get_card_archetype_score import get_card_archetype_score
from database.session import get_db
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from models.card import (
    Card,
    Card_Face,
    Card_Keyword,
    Face_Subtypes,
    Face_Supertypes,
    Face_Types,
)
from models.color import Color_Identity
from models.public_schemas import CardSchema, card_to_schema
from models.tag import Tag, TagRelation, Tagging
from collections import defaultdict
from collections.abc import Iterable

CARD_LOAD_OPTIONS = (
    selectinload(Card.taggings).selectinload(Tagging.tag),
    selectinload(Card.color_identity).selectinload(Color_Identity.color),
    selectinload(Card.keywords).selectinload(Card_Keyword.keyword),
    selectinload(Card.faces)
    .selectinload(Card_Face.supertypes)
    .selectinload(Face_Supertypes.type),
    selectinload(Card.faces)
    .selectinload(Card_Face.types)
    .selectinload(Face_Types.type),
    selectinload(Card.faces)
    .selectinload(Card_Face.subtypes)
    .selectinload(Face_Subtypes.type),
)

def load_inherited_tags_by_direct_id(
    db: Session,
    direct_tag_ids: Iterable[str],
) -> dict[str, list[Tag]]:
    requested_tag_ids = set(direct_tag_ids)

    if not requested_tag_ids:
        return {}

    tags_by_id = {
        tag.id: tag
        for tag in db.execute(select(Tag)).scalars()
    }
    parents_by_child: dict[str, list[str]] = defaultdict(list)

    for relation in db.execute(select(TagRelation)).scalars():
        parents_by_child[relation.child_id].append(relation.parent_id)

    ancestor_cache: dict[str, tuple[str, ...]] = {}

    def ancestor_ids(tag_id: str) -> tuple[str, ...]:
        if tag_id in ancestor_cache:
            return ancestor_cache[tag_id]

        ancestors: list[str] = []
        seen: set[str] = set()
        stack = list(parents_by_child.get(tag_id, []))

        while stack:
            parent_id = stack.pop()

            if parent_id in seen:
                continue

            seen.add(parent_id)
            ancestors.append(parent_id)
            stack.extend(parents_by_child.get(parent_id, []))

        ancestor_cache[tag_id] = tuple(ancestors)
        return ancestor_cache[tag_id]

    return {
        tag_id: [
            tags_by_id[ancestor_id]
            for ancestor_id in ancestor_ids(tag_id)
            if ancestor_id in tags_by_id
        ]
        for tag_id in requested_tag_ids
    }


def direct_tag_ids_for_cards(cards: Iterable[Card]) -> set[str]:
    return {
        tagging.tag_id
        for card in cards
        for tagging in card.taggings
    }

oracle_id = "3268251a-8292-44f9-9267-c961b182f739"

db = next(get_db())
create_database()

stmt = (
    select(Card)
    .options(*CARD_LOAD_OPTIONS)
    .where(Card.oracle_id == oracle_id)
)

card = db.execute(stmt).scalar_one_or_none()

if card is None:
    print("card not found")

inherited_tags_by_direct_id = load_inherited_tags_by_direct_id(
    db,
    direct_tag_ids_for_cards([card]),
)

schema = card_to_schema(card, inherited_tags_by_direct_id)

start_time = time.perf_counter()

result = get_card_archetype_score(schema)

end_time = time.perf_counter()

execution_time = end_time - start_time
print(f"Method took {execution_time:.6f} seconds to complete.")