from models.themes import Theme
from models.card import Card
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models.card import Card
from models.tag import Tagging
from models.themes import (
    Theme,
    ThemeCategory,
)
from models.themes import CardTheme
from database.session import session_scope


def theme_tag_ids(theme: Theme) -> set[str]:

    tag_ids = set()

    for category in theme.categories:
        for tag in category.tags:
            tag_ids.add(tag.id)

    return tag_ids

def card_tag_ids(card: Card) -> set[str]:

    return {
        tagging.tag_id
        for tagging in card.taggings
    }

def calculate_score(
    card_tag_ids: set[str],
    theme_tag_ids: set[str],
) -> int:

    return len(
        card_tag_ids.intersection(
            theme_tag_ids
        )
    )

def import_card_themes():

    with session_scope() as session:

        themes = session.scalars(
            select(Theme)
            .options(
                selectinload(Theme.categories)
                .selectinload(ThemeCategory.tags)
            )
        ).all()

        cards = session.scalars(
            select(Card)
            .options(
                selectinload(Card.taggings)
            )
        ).all()

        session.query(CardTheme).delete()

        theme_tag_map = {
            theme.id: theme_tag_ids(theme)
            for theme in themes
        }

        count = 0

        for card in cards:

            card_tags = card_tag_ids(card)

            for theme in themes:

                score = len(
                    card_tags &
                    theme_tag_map[theme.id]
                )

                if score == 0:
                    continue

                session.add(
                    CardTheme(
                        oracle_id=card.oracle_id,
                        theme_id=theme.id,
                        score=score,
                    )
                )

                count += 1

        session.commit()

        return count