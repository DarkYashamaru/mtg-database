from sqlalchemy import select
from database.session import session_scope
from models.themes import (
    Theme,
    ThemeCategory,
)

from models.tag import Tag


def import_theme(theme_id: int, theme_name: str, categories_data: dict[str, list[str]], curated: bool) -> int:

    imported_count = 0

    with session_scope() as session:

        theme = session.merge(
            Theme(
                id=theme_id,
                name=theme_name,
                curated=curated
            )
        )

        session.flush()

        category_id = 1

        for category_name, tag_ids in categories_data.items():

            category = (
                session.query(ThemeCategory)
                .filter(
                    ThemeCategory.theme_id == theme.id,
                    ThemeCategory.name == category_name,
                )
                .first()
            )

            if category is None:

                category = ThemeCategory(
                    id=category_id,
                    theme_id=theme.id,
                    name=category_name,
                )

                session.add(category)

            category.tags.clear()

            tags = session.scalars(
                select(Tag)
                .where(Tag.id.in_(tag_ids))
            ).all()

            tags_by_id = {tag.id: tag for tag in tags}

            missing = set(tag_ids) - set(tags_by_id)

            if missing:
                raise ValueError(
                    f"Missing tags for theme '{theme_name}' "
                    f"category '{category_name}': "
                    f"{sorted(missing)}"
                )

            category.tags.extend(tag for tag in tags if tag.is_active)

            imported_count += len(tags)

            category_id += 1

        session.commit()

    return imported_count
