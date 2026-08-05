from __future__ import annotations

from sqlalchemy import delete, select

from data.categories_data import CATEGORY_DATA
from database.create_database import create_database
from database.session import session_scope
from models.card import Card
from models.category import CardCategory, Category, CategoryTag
from models.tag import Tag, Tagging


def import_categories() -> int:
    create_database()

    with session_scope() as session:
        categories_by_name = {
            category.name: category
            for category in session.scalars(select(Category)).all()
        }

        for name in CATEGORY_DATA:
            if name not in categories_by_name:
                category = Category(name=name)
                session.add(category)
                session.flush()
                categories_by_name[name] = category

        existing_names = set(categories_by_name)
        configured_names = set(CATEGORY_DATA)
        for obsolete_name in existing_names - configured_names:
            session.delete(categories_by_name[obsolete_name])

        session.flush()

        session.execute(delete(CategoryTag))
        session.execute(delete(CardCategory))
        session.flush()

        tags_by_slug = {
            tag.slug: tag
            for tag in session.scalars(select(Tag)).all()
        }

        missing_tags: dict[str, list[str]] = {}
        inserted_category_tags = 0

        for name, tag_slugs in CATEGORY_DATA.items():
            category = categories_by_name[name]
            for slug in tag_slugs:
                tag = tags_by_slug.get(slug)
                if tag is None:
                    missing_tags.setdefault(name, []).append(slug)
                    continue
                session.add(CategoryTag(category_id=category.id, tag_id=tag.id))
                inserted_category_tags += 1

        if missing_tags:
            missing_lines = [
                f"{category}: {sorted(slugs)}"
                for category, slugs in sorted(missing_tags.items())
            ]
            raise ValueError(
                "Missing tags in categories seed:\n" + "\n".join(missing_lines)
            )

        category_ids_by_tag_id: dict[str, set[int]] = {}
        for name, tag_slugs in CATEGORY_DATA.items():
            category_id = categories_by_name[name].id
            for slug in tag_slugs:
                tag = tags_by_slug[slug]
                category_ids_by_tag_id.setdefault(tag.id, set()).add(category_id)

        existing_oracle_ids = set(session.scalars(select(Card.oracle_id)).all())
        card_category_pairs: set[tuple[str, int]] = set()
        for tagging in session.scalars(select(Tagging)).all():
            if tagging.oracle_id not in existing_oracle_ids:
                continue
            for category_id in category_ids_by_tag_id.get(tagging.tag_id, ()):
                card_category_pairs.add((tagging.oracle_id, category_id))

        session.add_all(
            CardCategory(oracle_id=oracle_id, category_id=category_id)
            for oracle_id, category_id in sorted(card_category_pairs)
        )

        return inserted_category_tags
