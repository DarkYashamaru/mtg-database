from __future__ import annotations

from typing import Any
import requests
from sqlalchemy import select
from tools.logger import logger
from database.create_database import create_database
from database.session import session_scope
from models.themes import Theme

EDHREC_TAGS_URL = "https://json.edhrec.com/pages/tags.json"


def extract_slug(url: str) -> str:
    """
    Convert '/tags/plus-1-plus-1-counters' -> 'plus-1-plus-1-counters'
    """
    return url.rstrip("/").split("/")[-1]


def iter_edhrec_theme_rows(payload: dict[str, Any]):
    """
    Yield unique (slug, display_name) pairs from EDHREC tags.json.
    The slug is what we store in Theme.name.
    """
    seen_slugs: set[str] = set()

    cardlists = payload.get("container", {}).get("json_dict", {}).get("cardlists", [])

    for cardlist in cardlists:
        for item in cardlist.get("cardviews", []):
            url = item.get("url")
            if not url:
                continue

            slug = extract_slug(url)
            if not slug or slug in seen_slugs:
                continue

            seen_slugs.add(slug)
            display_name = item.get("name", slug)

            yield slug, display_name


def upsert_theme(session, name: str, curated: bool = False) -> bool:
    """
    Insert the theme if it does not exist.
    Returns True if inserted, False if it already existed.
    """
    existing = session.scalar(
        select(Theme).where(Theme.name == name)
    )

    if existing is not None:
        # Keep curated=True if it was ever marked curated.
        if curated and not existing.curated:
            existing.curated = True
        return False

    session.add(
        Theme(
            name=name,
            curated=curated,
        )
    )
    return True


def import_edhrec_themes() -> int:
    response = requests.get(EDHREC_TAGS_URL, timeout=30)
    response.raise_for_status()

    payload = response.json()

    imported_count = 0

    with session_scope() as session:
        for slug, display_name in iter_edhrec_theme_rows(payload):
            inserted = upsert_theme(
                session=session,
                name=slug,        # store slug as the theme name
                curated=False,    # EDHREC-imported themes start uncategorized
            )

            if inserted:
                imported_count += 1
                logger.info(f"Imported theme: {display_name} -> {slug}")

        session.commit()
        session.expunge_all()

    return imported_count


def main() -> int:
    create_database()
    count = import_edhrec_themes()
    logger.info(f"Imported {count} themes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())