from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import requests
from database.create_database import create_database
from database.session import get_db
from sqlalchemy.orm import Session
from sqlalchemy import select
from tools.card_to_slug import card_name_to_slug, get_primary_card_name

from models.card import (
    Card,
    Card_Face,
    Card_Keyword,
    Face_Subtypes,
    Face_Supertypes,
    Face_Types,
)
from models.color import Color_Identity
from models.tag import Tag, TagRelation, Tagging
from models.themes import Theme, ThemeCategory, ThemeCategoryTag, CardTheme
import re

headers = ["New Commanders", "Top Commanders", "New Cards", "High Synergy Cards", "Top Cards", "Game Changers", "Creatures", "Instants", "Sorceries", "Utility Artifacts", "Enchantments", "Planeswalkers", "Utility Lands", "Mana Artifacts", "Lands"]


def main() -> int:
    # 3. Initialize Database
    create_database()
    db: Session = next(get_db())

    all_themes = db.scalars(select(Theme)).all()
    all_cards = db.scalars(select(Card)).all()

    card_dict = {}
    for card in all_cards:
        primary = get_primary_card_name(card.name)
        card_dict[primary] = card.oracle_id
        card_dict[card.name] = card.oracle_id

    current = 0
    max_loop = 1

    # Temporary storage to deduplicate: {(oracle_id, theme_id): score}
    pending_card_themes = {}

    for theme in all_themes:
        slug = card_name_to_slug(theme.name)
        print(f"Working on theme {slug}")

        #if current > max_loop:
         #   break

        url = f"https://json.edhrec.com/pages/tags/{slug}.json"
        response = requests.get(url, timeout=5, allow_redirects=True)
        item = response.json()

        for cardlist in item["container"]["json_dict"]["cardlists"]:
            if cardlist["header"] in headers:
                target = cardlist["cardviews"]
                for card in target:
                    name = card["name"]
                    primary_name = get_primary_card_name(name)

                    print(f"Card: {name}")

                    matched_name = None
                    if name in card_dict:
                        matched_name = name
                    elif primary_name in card_dict:
                        matched_name = primary_name

                    if matched_name:
                        oracle_id = card_dict[matched_name]
                        theme_id = theme.id
                        score = card["inclusion"]

                        # Create a unique tracking key for this pairing
                        pair_key = (oracle_id, theme_id)

                        # Keeps the highest score if the card appears multiple times
                        if pair_key in pending_card_themes:
                            pending_card_themes[pair_key] = max(pending_card_themes[pair_key], score)
                        else:
                            pending_card_themes[pair_key] = score

        current += 1

    # Now that everything is cleanly deduplicated, merge into the database session safely
    for (oracle_id, theme_id), score in pending_card_themes.items():
        card_theme = CardTheme(
            oracle_id=oracle_id,
            theme_id=theme_id,
            score=score
        )
        db.merge(card_theme)

    db.commit()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())