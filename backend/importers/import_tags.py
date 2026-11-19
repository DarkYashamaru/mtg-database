from __future__ import annotations

from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
from database.create_database import create_database  # noqa: E402
from downloaders.download_oracle_tags import ORACLE_TAGS_PATH  # noqa: E402
from importers.scryfall_bulk_reader import load_scryfall_bulk_items  # noqa: E402
from database.session import DATABASE_PATH, session_scope  # noqa: E402
from models.tag import Tag, TagRelation, Tagging  # noqa: E402
from sqlalchemy import delete, select, update

DEFAULT_BATCH_SIZE = 500

def import_oracle_tags(
    source_path: Path = ORACLE_TAGS_PATH,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> int:
    if batch_size < 1:
        raise ValueError("batch_size must be greater than 0.")

    if not source_path.exists():
        raise FileNotFoundError(
            f"Oracle tags bulk file not found at {source_path}."
        )

    create_database()

    payload = load_scryfall_bulk_items(source_path)

    oracle_tags = [item for item in payload if item.get("type") == "oracle"]
    imported_count = len(oracle_tags)

    with session_scope() as session:
        tags_by_id = {tag.id: tag for tag in session.scalars(select(Tag)).all()}
        session.execute(update(Tag).values(is_active=False))

        for item in oracle_tags:
            tag = _tag_from_scryfall(item)
            if tag is None:
                continue
            existing = tags_by_id.get(tag.id)
            if existing is None:
                session.add(tag)
                continue
            existing.slug = tag.slug
            existing.label = tag.label
            existing.description = tag.description
            existing.is_active = True

        session.flush()
        session.execute(delete(TagRelation))
        session.execute(delete(Tagging))

        for item in oracle_tags:
            tag_id = item.get("id")
            if not tag_id:
                continue
            session.add_all(
                TagRelation(parent_id=parent_id, child_id=tag_id)
                for parent_id in item.get("parent_ids") or []
            )
            session.add_all(
                Tagging(
                    tag_id=tag_id,
                    oracle_id=tagging["oracle_id"],
                    annotation=tagging.get("annotation"),
                )
                for tagging in item.get("taggings") or []
                if tagging.get("oracle_id")
            )

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
