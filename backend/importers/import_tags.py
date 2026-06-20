from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
from database.create_database import create_database  # noqa: E402
from database.session import DATABASE_PATH, session_scope  # noqa: E402
from models.tag import Tag, TagRelation, Tagging  # noqa: E402
from sqlalchemy import select

DEFAULT_BATCH_SIZE = 500

ORACLE_TAGS_PATH = (
    PROJECT_ROOT / "downloads" / "scryfall" / "oracle_tags.json"
)


def import_oracle_tags(
    source_path: Path = ORACLE_TAGS_PATH,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> int:
    if batch_size < 1:
        raise ValueError("batch_size must be greater than 0.")

    if not source_path.exists():
        raise FileNotFoundError(
            f"Oracle tags JSON not found at {source_path}."
        )

    create_database()

    with source_path.open(encoding="utf-8") as file:
        payload = json.load(file)

    imported_count = 0

    with session_scope() as session:

        #
        # Pass 1: Tags
        #

        all_ids = set(session.scalars( select(Tag.id)).all() )

        for item in payload:

            id = item.get("id")

            if id in all_ids:
                continue

            tag = _tag_from_scryfall(item)

            if tag is None:
                continue

            session.merge(tag)

            imported_count += 1

            if imported_count % batch_size == 0:
                session.commit()
                session.expunge_all()

        session.commit()

        #
        # Pass 2: Relationships
        #

        existing_relations = {
            (r.parent_id, r.child_id)
            for r in session.scalars(select(TagRelation)).all()
        }

        existing_taggings = {
            (t.tag_id, t.oracle_id)
            for t in session.scalars(select(Tagging)).all()
        }

        processed = 0

        for item in payload:
            if item.get("type") != "oracle":
                continue

            tag_id = item.get("id")
            if not tag_id:
                continue

            #
            # Parent relationships
            #
            for parent_id in item.get("parent_ids") or []:

                key = (parent_id, tag_id)

                if key in existing_relations:
                    continue

                session.add(
                    TagRelation(
                        parent_id=parent_id,
                        child_id=tag_id,
                    )
                )

                existing_relations.add(key)

            #
            # Card taggings
            #
            for tagging in item.get("taggings") or []:
                oracle_id = tagging.get("oracle_id")

                if not oracle_id:
                    continue

                key = (tag_id, oracle_id)

                if key in existing_taggings:
                    continue

                session.add(
                    Tagging(
                        tag_id=tag_id,
                        oracle_id=oracle_id,
                        annotation=tagging.get("annotation"),
                    )
                )

                existing_taggings.add(key)

            processed += 1

            if processed % batch_size == 0:
                session.commit()
                session.expunge_all()

    return imported_count


def _tag_from_scryfall(item: dict[str, Any]) -> Tag | None:
    if item.get("type") != "oracle":
        return None

    tag_id = item.get("id")
    if not tag_id:
        return None

    return Tag(
        id=tag_id,
        slug=item.get("slug") or "",
        label=item.get("label") or "",
        description=item.get("description"),
    )