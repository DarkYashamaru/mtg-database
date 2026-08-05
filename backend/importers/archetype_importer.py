from __future__ import annotations

from sqlalchemy import delete, select

from data.archetypes_data import ARCHETYPE_DATA
from database.create_database import create_database
from database.session import session_scope
from models.archetype import Archetype, ArchetypeTag, CardArchetype
from models.card import Card
from models.tag import Tag, Tagging


def import_archetypes() -> int:
    create_database()

    with session_scope() as session:
        archetypes_by_name = {
            archetype.name: archetype
            for archetype in session.scalars(select(Archetype)).all()
        }

        for name in ARCHETYPE_DATA:
            if name not in archetypes_by_name:
                archetype = Archetype(name=name)
                session.add(archetype)
                session.flush()
                archetypes_by_name[name] = archetype

        existing_names = set(archetypes_by_name)
        configured_names = set(ARCHETYPE_DATA)
        for obsolete_name in existing_names - configured_names:
            session.delete(archetypes_by_name[obsolete_name])

        session.flush()

        session.execute(delete(ArchetypeTag))
        session.execute(delete(CardArchetype))
        session.flush()

        tags_by_slug = {
            tag.slug: tag
            for tag in session.scalars(select(Tag)).all()
        }

        missing_tags: dict[str, list[str]] = {}
        inserted_archetype_tags = 0

        for name, tag_slugs in ARCHETYPE_DATA.items():
            archetype = archetypes_by_name[name]
            for slug in tag_slugs:
                tag = tags_by_slug.get(slug)
                if tag is None:
                    missing_tags.setdefault(name, []).append(slug)
                    continue
                session.add(ArchetypeTag(archetype_id=archetype.id, tag_id=tag.id))
                inserted_archetype_tags += 1

        if missing_tags:
            missing_lines = [
                f"{archetype}: {sorted(slugs)}"
                for archetype, slugs in sorted(missing_tags.items())
            ]
            raise ValueError(
                "Missing tags in archetypes seed:\n" + "\n".join(missing_lines)
            )

        archetype_ids_by_tag_id: dict[str, set[int]] = {}
        for name, tag_slugs in ARCHETYPE_DATA.items():
            archetype_id = archetypes_by_name[name].id
            for slug in tag_slugs:
                tag = tags_by_slug[slug]
                archetype_ids_by_tag_id.setdefault(tag.id, set()).add(archetype_id)

        existing_oracle_ids = set(session.scalars(select(Card.oracle_id)).all())
        card_archetype_pairs: set[tuple[str, int]] = set()
        for tagging in session.scalars(select(Tagging)).all():
            if tagging.oracle_id not in existing_oracle_ids:
                continue
            for archetype_id in archetype_ids_by_tag_id.get(tagging.tag_id, ()):
                card_archetype_pairs.add((tagging.oracle_id, archetype_id))

        session.add_all(
            CardArchetype(oracle_id=oracle_id, archetype_id=archetype_id)
            for oracle_id, archetype_id in sorted(card_archetype_pairs)
        )

        return inserted_archetype_tags
