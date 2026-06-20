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
from models.themes import Theme, ThemeCategory, ThemeCategoryTag, CommanderTheme
import re
from tools.logger import logger

HEADERS = {
    "New Commanders",
    "Top Commanders", 
    "New Cards", 
    "High Synergy Cards", 
    "Top Cards", 
    "Game Changers", 
    "Creatures", 
    "Instants", 
    "Sorceries", 
    "Utility Artifacts", 
    "Enchantments", 
    "Planeswalkers", 
    "Utility Lands", 
    "Mana Artifacts", 
    "Lands"
}

def precompute_commander_theme_edhrec(db: Session )->None:

    all_themes = db.scalars(select(Theme)).all()
    all_cards = db.scalars(select(Card)).all()
    all_commander_themes = db.scalars(select(CommanderTheme)).all()

    card_dict = {}
    for card in all_cards:
        primary = get_primary_card_name(card.name)
        card_dict[primary] = card.oracle_id
        card_dict[card.name] = card.oracle_id

    theme_dict = {}
    for theme in all_themes:
        theme_dict[theme.name] = theme.id

    commander_theme_set = set()
    for commander_theme in all_commander_themes:
        commander_theme_set.add(commander_theme.oracle_id)

    current = 0
    max_loop = 1

    commanders:list[Card] = []

    for card in all_cards:

        if card.oracle_id in commander_theme_set:
            continue

        face = card.faces[0]

        superTypes = face.supertypes
        types = face.types

        legendary = False
        creature = False

        for superType in superTypes:
            if superType.type.value == "Legendary":
                legendary = True
                break

        for type in types:
            if type.type.value == "Creature":
                creature = True

        if legendary and creature:
            commanders.append(card)

    current = 0
    max_loops = 1

    pending_commander_themes = {}

    for commander in commanders:

        if commander.oracle_id in commander_theme_set:
            logger.info(f"{commander.name} Already in database, skipping")
            continue

        #if current > max_loops:
         #   break

        try:
            slug = card_name_to_slug(get_primary_card_name(commander.name))
            url = f"https://json.edhrec.com/pages/commanders/{slug}.json"

            logger.info(f"Getting data for {commander.name} slug: {slug}")

            response = requests.get(url, timeout=120, allow_redirects=True)
            item = response.json()

            for tag_links in item["panels"]["taglinks"]:

                slug = tag_links["slug"]
                id = commander.oracle_id

                key_pair = (id, theme_dict[slug])

                if key_pair in commander_theme_set:
                    logger.info(f"Already in database, skipping")
                    continue

                pending_commander_themes[key_pair] = tag_links["count"]
        except Exception as e:
            logger.info(e)

        current += 1

    
    for (oracle_id, theme_id), score in pending_commander_themes.items():
        card_theme = CommanderTheme(
             oracle_id=oracle_id,
             theme_id=theme_id,
             score=score
         )
        db.merge(card_theme)

    db.commit()



def main() -> int:
    # 3. Initialize Database
    create_database()
    db: Session = next(get_db())
    precompute_commander_theme_edhrec(db)
    # # Temporary storage to deduplicate: {(oracle_id, theme_id): score}
    # pending_card_themes = {}

    # for theme in all_themes:
    #     slug = card_name_to_slug(theme.name)
    #     logger.info(f"Working on theme {slug}")

    #     #if current > max_loop:
    #      #   break

    #     url = f"https://json.edhrec.com/pages/tags/{slug}.json"
    #     response = requests.get(url, timeout=5, allow_redirects=True)
    #     item = response.json()

    #     for cardlist in item["container"]["json_dict"]["cardlists"]:
    #         if cardlist["header"] in headers:
    #             target = cardlist["cardviews"]
    #             for card in target:
    #                 name = card["name"]
    #                 primary_name = get_primary_card_name(name)

    #                 logger.info(f"Card: {name}")

    #                 matched_name = None
    #                 if name in card_dict:
    #                     matched_name = name
    #                 elif primary_name in card_dict:
    #                     matched_name = primary_name

    #                 if matched_name:
    #                     oracle_id = card_dict[matched_name]
    #                     theme_id = theme.id
    #                     score = card["inclusion"]

    #                     # Create a unique tracking key for this pairing
    #                     pair_key = (oracle_id, theme_id)

    #                     # Keeps the highest score if the card appears multiple times
    #                     if pair_key in pending_card_themes:
    #                         pending_card_themes[pair_key] = max(pending_card_themes[pair_key], score)
    #                     else:
    #                         pending_card_themes[pair_key] = score

    #     current += 1

    # # Now that everything is cleanly deduplicated, merge into the database session safely
    # for (oracle_id, theme_id), score in pending_card_themes.items():
    #     card_theme = CardTheme(
    #         oracle_id=oracle_id,
    #         theme_id=theme_id,
    #         score=score
    #     )
    #     db.merge(card_theme)

    # db.commit()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())