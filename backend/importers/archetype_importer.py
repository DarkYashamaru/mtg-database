from sqlalchemy import select

from database.session import session_scope

from models.archetypes import (
    Archetype,
    ArchetypeCategory,
)

from models.tag import Tag


def import_archetype(
    archetype_id: int,
    archetype_name: str,
    categories_data: dict[str, list[str]]
) -> int:

    imported_count = 0

    with session_scope() as session:

        archetype = session.merge(
            Archetype(
                id=archetype_id,
                name=archetype_name,
            )
        )

        session.flush()

        category_id = 1

        for category_name, tag_slugs in categories_data.items():

            category = (
                session.query(ArchetypeCategory)
                .filter(
                    ArchetypeCategory.archetype_id == archetype.id,
                    ArchetypeCategory.name == category_name,
                )
                .first()
            )

            if category is None:

                category = ArchetypeCategory(
                    id=category_id,
                    archetype_id=archetype.id,
                    name=category_name,
                )

                session.add(category)

            category.tags.clear()

            tags = session.scalars(
                select(Tag)
                .where(Tag.slug.in_(tag_slugs))
            ).all()

            found_slugs = {tag.slug for tag in tags}

            missing = set(tag_slugs) - found_slugs

            if missing:
                raise ValueError(
                    f"Missing tags for archetype '{archetype_name}' "
                    f"category '{category_name}': "
                    f"{sorted(missing)}"
                )

            category.tags.extend(tags)

            imported_count += len(tags)

            category_id += 1

        session.commit()

    return imported_count