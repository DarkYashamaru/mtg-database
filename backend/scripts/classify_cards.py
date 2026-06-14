import argparse
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
import sys
import time

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from database.create_database import create_database
from database.session import get_db
from models.card import (
    Card,
    Card_Face,
    Card_Keyword,
    Face_Subtypes,
    Face_Supertypes,
    Face_Types,
)
from models.color import Color_Identity
from models.public_schemas import card_to_schema
from models.tag import Tag, TagRelation, Tagging
from services.ai.classification.get_card_archetype_score import (
    DEFAULT_MODEL,
    DEFAULT_OLLAMA_URL,
    get_card_archetype_score,
)


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classify one MTG card into Commander archetype scores.",
    )
    lookup = parser.add_mutually_exclusive_group()
    lookup.add_argument(
        "--oracle-id",
        default="3268251a-8292-44f9-9267-c961b182f739",
        help="Oracle ID to classify.",
    )
    lookup.add_argument(
        "--name",
        help="Exact card name to classify. Falls back to a contains match.",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print the Ollama prompt and raw model JSON.",
    )
    return parser.parse_args()


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


def load_card_by_oracle_id(db: Session, oracle_id: str) -> Card | None:
    stmt = (
        select(Card)
        .options(*CARD_LOAD_OPTIONS)
        .where(Card.oracle_id == oracle_id)
    )
    return db.execute(stmt).scalar_one_or_none()


def load_card_by_name(db: Session, name: str) -> Card | None:
    exact_stmt = (
        select(Card)
        .options(*CARD_LOAD_OPTIONS)
        .where(func.lower(Card.name) == name.lower())
    )
    card = db.execute(exact_stmt).scalar_one_or_none()

    if card is not None:
        return card

    contains_stmt = (
        select(Card)
        .options(*CARD_LOAD_OPTIONS)
        .where(Card.name.ilike(f"%{name}%"))
        .order_by(Card.name)
        .limit(2)
    )
    matches = list(db.execute(contains_stmt).scalars())

    if len(matches) > 1:
        names = ", ".join(card.name for card in matches)
        raise ValueError(f"Multiple cards matched {name!r}: {names}")

    return matches[0] if matches else None


def main() -> int:
    args = parse_args()

    create_database()
    db = next(get_db())

    try:
        card = (
            load_card_by_name(db, args.name)
            if args.name
            else load_card_by_oracle_id(db, args.oracle_id)
        )

        if card is None:
            print("Card not found.")
            return 1

        inherited_tags_by_direct_id = load_inherited_tags_by_direct_id(
            db,
            direct_tag_ids_for_cards([card]),
        )
        schema = card_to_schema(card, inherited_tags_by_direct_id)

        start_time = time.perf_counter()
        result = get_card_archetype_score(
            schema,
            model=args.model,
            ollama_url=args.ollama_url,
            timeout_seconds=args.timeout,
            verbose=args.verbose,
        )
        execution_time = time.perf_counter() - start_time

        print(f"Card: {schema.name}")
        print(result.model_dump_json(indent=2))
        print(f"Method took {execution_time:.3f} seconds.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
