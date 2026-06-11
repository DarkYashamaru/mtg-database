from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Iterable
from database.create_database import create_database  # noqa: E402
from database.session import session_scope  # noqa: E402
from models.card import Card  # noqa: E402
from models.card_face import Card_Face
from downloaders.download_oracle_cards import ORACLE_CARDS_PATH  # noqa: E402
from sqlalchemy import select
from models.color import Color, Color_Identity
from functools import cache
from models.catalogs import KeywordAbility, KeywordAction, Supertype, CardType, Subtype
from models.card_type import Card_Supertypes, Card_Subtypes, Card_Types

unique_keywords = set()

def parse_types(text, valid_subtypes):
    words = text.split()

    @cache
    def parse_from(i):
        if i >= len(words):
            return ()

        for j in range(len(words), i, -1):
            candidate = " ".join(words[i:j])

            if candidate in valid_subtypes:
                rest = parse_from(j)

                if rest is not None:
                    return (candidate,) + rest

        return None

    result = parse_from(0)

    if result is None:
        raise ValueError(f"Could not parse: {text}")

    return list(result)


def import_oracle_cards(source_path: Path = ORACLE_CARDS_PATH) -> int:

    if not source_path.exists():
        raise FileNotFoundError(
            f"Oracle cards JSON not found at {source_path}. "
            "Run backend/services/scryfall.py first."
        )

    colors: list[Color] = []
    supertypes: list[Supertype] = []
    cardtypes: list[CardType] = []
    subtypes: list[Subtype] = []

    with session_scope() as session:
        colors = session.scalars(select(Color)).all()
        supertypes = session.scalars(select(Supertype)).all()
        cardtypes = session.scalars(select(CardType)).all()
        subtypes = session.scalars(select(Subtype)).all()

    color_dict = {color.symbol: color.id for color in colors}

    supertype_list = []
    cardtype_list = []
    subtype_list = []

    for type in supertypes:
        supertype_list.append(type.value)

    for type in cardtypes:
        cardtype_list.append(type.value)

    for type in subtypes:
        subtype_list.append(type.value)

    with source_path.open(encoding="utf-8") as file:
        payload = json.load(file)

    limit = 10
    current = 0

    imported_count = 0
    with session_scope() as session:

        for item in payload:

            if current >= limit:
                break

            card = _card_from_scryfall(item)
            if not card:
                continue

            oracle_id = item.get("oracle_id")

            keywords = item.get('keywords')

            color_identity = item.get('color_identity')

            if color_identity:
                for color in color_identity:
                    identity = Color_Identity(color_id = color_dict[color], card_id = oracle_id)
                    session.merge(identity)
                    #print(identity)

            if keywords:
                unique_keywords.update(keywords)

            session.merge(card)
            car_faces = get_card_faces(item)

            for face in car_faces:
                session.merge(face)
                print(f"Importing {face.name}")

            type_line = item.get("type_line")

            print(type_line)

            left, _, right = type_line.partition("—")

            left = left.strip()
            right = right.strip()
            tokens = left.split()

            supertypes_result = []
            cardtypes_result = []
            subtypes_result = []

            supertypes_result = [t for t in tokens if t in supertype_list]
            cardtypes_result = [t for t in tokens if t in cardtype_list]

            if right:
                subtypes_result = parse_types(right, subtype_list)

            if supertypes_result:
                print(f"Super Types: {supertypes_result}")

                for type in supertypes_result:
                    session.merge(Card_Supertypes(card_id=oracle_id, type_id=type))

            if cardtypes_result:
                print(f"Card Types: {cardtypes_result}")
                for type in cardtypes_result:
                    session.merge(Card_Types(card_id=oracle_id, type_id=type))

            if subtypes_result:
                print(f"Sub Types: {subtypes_result}")
                for type in subtypes_result:
                    session.merge(Card_Subtypes(card_id=oracle_id, type_id=type))

            imported_count += 1
            current +=1


        session.commit()
        session.expunge_all()

    return imported_count


def _card_from_scryfall(item: dict[str, Any]) -> Card | None:
    oracle_id = item.get("oracle_id")
    if not oracle_id:
        return None
    
    legalities = item.get("legalities") or {}
    commander_legal = legalities.get("commander") == "legal"

    if not commander_legal:
        return None
    
    card_layout = item.get("layout") or ""
    if card_layout == "" or card_layout == "art_series" or card_layout == "token" or card_layout == "scheme":
        return None

    front_face = _front_face(item)

    return Card(
        oracle_id=oracle_id,
        name=item.get("name") or front_face.get("name") or "",
        mana_cost=item.get("mana_cost") or front_face.get("mana_cost"),
        cmc=float(item.get("cmc") or 0),
        oracle_text=item.get("oracle_text") or front_face.get("oracle_text"),
        layout=card_layout,
        power=item.get("power") or front_face.get("power"),
        toughness=item.get("toughness") or front_face.get("toughness"),
        type_line=item.get("type_line") or front_face.get("type_line"),
        commander_legal=commander_legal,
        standard_legal=legalities.get("standard") == "legal",
        released_at=_parse_date(item.get("released_at")),
    )

def get_card_faces(item: dict[str, Any]) -> list[Card_Face]:

    oracle_id = item.get("oracle_id")
    card_faces = item.get("card_faces")

    result:list[Card_Face] = []

    valid_faces = []

    if isinstance(card_faces, list) and card_faces:
        for face in card_faces:
            if isinstance(face, dict):
                valid_faces.append(face)

    for valid_face in valid_faces:

        face = Card_Face(
            parent_id=oracle_id,
            mana_cost=valid_face.get("mana_cost"),
            cmc=float(valid_face.get("cmc") or 0),
            name=valid_face.get("name"),
            oracle_text=valid_face.get("oracle_text"),
            power=valid_face.get("power"),
            toughness=valid_face.get("toughness"),
            type_line=valid_face.get("type_line"),
        )

        result.append(face)

    if len(result) < 1:
            
            face = Card_Face(
                parent_id=oracle_id,
                mana_cost=item.get("mana_cost"),
                cmc=float(item.get("cmc") or 0),
                name=item.get("name"),
                oracle_text=item.get("oracle_text"),
                power=item.get("power"),
                toughness=item.get("toughness"),
                type_line=item.get("type_line"),
            )
            result.append(face)

    return result


def _front_face(item: dict[str, Any]) -> dict[str, Any]:
    card_faces = item.get("card_faces")
    if isinstance(card_faces, list) and card_faces:
        first_face = card_faces[0]
        if isinstance(first_face, dict):
            return first_face

    return {}


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None

    return date.fromisoformat(value)
