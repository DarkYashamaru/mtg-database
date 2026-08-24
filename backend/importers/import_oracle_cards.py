from __future__ import annotations

from datetime import datetime, timezone
from functools import cache
from pathlib import Path
from typing import Any

from database.session import session_scope
from downloaders.download_oracle_cards import ORACLE_CARDS_PATH
from importers.scryfall_bulk_reader import load_scryfall_bulk_items
from models.card import (
    Card,
    Card_Face,
    Card_Keyword,
    Card_Type_Collection,
    Face_Subtypes,
    Face_Supertypes,
    Face_Types,
)
from models.catalogs import CardType, Subtype, Supertype
from models.color import Color, Color_Identity
from sqlalchemy import select
from tools.logger import logger

supertype_list: list[str] = []
cardtype_list: list[str] = []
subtype_list: list[str] = []
SHARED_FRONT_IMAGE_LAYOUTS = {"prepare", "prepared", "room", "adventure"}


def parse_types(text: str, valid_subtypes: list[str]) -> list[str]:
    words = text.split()

    @cache
    def parse_from(i: int):
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
    global supertype_list
    global cardtype_list
    global subtype_list

    if not source_path.exists():
        raise FileNotFoundError(
            f"Oracle cards bulk file not found at {source_path}. "
            "Run backend/services/scryfall.py first."
        )

    with session_scope() as session:
        colors = session.scalars(select(Color)).all()
        supertypes = session.scalars(select(Supertype)).all()
        cardtypes = session.scalars(select(CardType)).all()
        subtypes = session.scalars(select(Subtype)).all()

        all_cards = session.scalars(select(Card)).all()

    color_dict = {color.symbol: color.id for color in colors}
    supertype_list = [type_.value for type_ in supertypes]
    cardtype_list = [type_.value for type_ in cardtypes]
    subtype_list = [type_.value for type_ in subtypes]

    oracle_ids = set()

    for card in all_cards:
        oracle_ids.add(card.oracle_id)

    payload = load_scryfall_bulk_items(source_path)

    imported_count = 0

    with session_scope() as session:
        for item in payload:
            oracle_id = item.get("oracle_id")
            if not oracle_id:
                continue

            if oracle_id in oracle_ids:
                continue

            card = _card_from_scryfall(item)
            if not card:
                continue

            keywords = item.get("keywords")
            if keywords:
                for keyword in keywords:
                    session.merge(Card_Keyword(card_id=oracle_id, keyword_value=keyword))

            color_identity = item.get("color_identity")
            if color_identity:
                for color in color_identity:
                    identity = Color_Identity(
                        color_id=color_dict[color],
                        card_id=oracle_id,
                    )
                    session.merge(identity)

            session.merge(card)

            card_faces = get_card_faces(item)

            for face in card_faces:
                session.merge(face)
                logger.info(f"Importing {face.name}")

            types_to_add: list[Card_Type_Collection] = []

            if len(card_faces) == 1:
                types_to_add.append(parse_card_types(item.get("type_line") or "", card_faces[0]))
            else:
                for face in card_faces:
                    types_to_add.append(parse_card_types(face.type_line or "", face))

            for collection in types_to_add:
                for type_ in collection.super_types:
                    session.merge(type_)
                for type_ in collection.card_types:
                    session.merge(type_)
                for type_ in collection.sub_types:
                    session.merge(type_)

            imported_count += 1

        session.commit()
        session.expunge_all()

    return imported_count


def backfill_shared_front_face_images(source_path: Path = ORACLE_CARDS_PATH) -> int:
    if not source_path.exists():
        raise FileNotFoundError(
            f"Oracle cards bulk file not found at {source_path}. "
            "Run backend/services/scryfall.py first."
        )

    payload = load_scryfall_bulk_items(source_path)
    updated_faces = 0

    with session_scope() as session:
        for item in payload:
            oracle_id = item.get("oracle_id")
            if not oracle_id:
                continue

            layout = (item.get("layout") or "").strip().lower()
            if layout not in SHARED_FRONT_IMAGE_LAYOUTS:
                continue

            legalities = item.get("legalities") or {}
            if legalities.get("commander") != "legal":
                continue

            root_image_uris = item.get("image_uris") or {}
            if not root_image_uris:
                continue

            faces = session.scalars(
                select(Card_Face).where(Card_Face.parent_id == oracle_id)
            ).all()

            if not faces:
                continue

            for face in faces:
                changed = False

                if not face.small_image and root_image_uris.get("small"):
                    face.small_image = root_image_uris.get("small")
                    changed = True

                if not face.normal_image and root_image_uris.get("normal"):
                    face.normal_image = root_image_uris.get("normal")
                    changed = True

                if not face.large_image and root_image_uris.get("large"):
                    face.large_image = root_image_uris.get("large")
                    changed = True

                if changed:
                    updated_faces += 1

        session.commit()

    return updated_faces


def _card_from_scryfall(item: dict[str, Any]) -> Card | None:
    oracle_id = item.get("oracle_id")
    if not oracle_id:
        return None

    legalities = item.get("legalities") or {}
    commander_legal = legalities.get("commander") == "legal"

    if not commander_legal:
        return None

    card_layout = item.get("layout") or ""
    if card_layout in {"", "art_series", "token", "scheme"}:
        return None

    return Card(
        oracle_id=oracle_id,
        name=item.get("name"),
        cmc=float(item.get("cmc") or 0),
        layout=card_layout,
        commander_legal=commander_legal,
        standard_legal=legalities.get("standard") == "legal",
    )


def parse_card_types(type_line: str, face: Card_Face) -> Card_Type_Collection:
    result: Card_Type_Collection = Card_Type_Collection()

    left, _, right = type_line.partition("—")
    left = left.strip()
    right = right.strip()
    tokens = left.split()

    supertypes_result = [t for t in tokens if t in supertype_list]
    cardtypes_result = [t for t in tokens if t in cardtype_list]
    subtypes_result: list[str] = []

    if right:
        subtypes_result = parse_types(right, subtype_list)

    if supertypes_result:
        for type_ in supertypes_result:
            result.super_types.append(
                Face_Supertypes(card_id=face.parent_id, face_name=face.name, type_id=type_)
            )

    if cardtypes_result:
        for type_ in cardtypes_result:
            result.card_types.append(
                Face_Types(card_id=face.parent_id, face_name=face.name, type_id=type_)
            )

    if subtypes_result:
        for type_ in subtypes_result:
            result.sub_types.append(
                Face_Subtypes(card_id=face.parent_id, face_name=face.name, type_id=type_)
            )

    return result


def get_card_faces(item: dict[str, Any]) -> list[Card_Face]:
    oracle_id = item.get("oracle_id")
    card_faces = item.get("card_faces")
    layout = (item.get("layout") or "").strip().lower()
    root_image_uris = item.get("image_uris") or {}

    result: list[Card_Face] = []
    valid_faces: list[dict[str, Any]] = []

    if isinstance(card_faces, list) and card_faces:
        for face in card_faces:
            if isinstance(face, dict):
                valid_faces.append(face)

    for valid_face in valid_faces:
        image_uris = valid_face.get("image_uris") or {}

        if layout in SHARED_FRONT_IMAGE_LAYOUTS and root_image_uris:
            image_uris = {
                "small": image_uris.get("small") or root_image_uris.get("small"),
                "normal": image_uris.get("normal") or root_image_uris.get("normal"),
                "large": image_uris.get("large") or root_image_uris.get("large"),
            }

        face = Card_Face(
            parent_id=oracle_id,
            mana_cost=valid_face.get("mana_cost"),
            cmc=float(valid_face.get("cmc") or 0),
            name=valid_face.get("name"),
            oracle_text=valid_face.get("oracle_text"),
            power=valid_face.get("power"),
            toughness=valid_face.get("toughness"),
            type_line=valid_face.get("type_line"),
            small_image=image_uris.get("small"),
            normal_image=image_uris.get("normal"),
            large_image=image_uris.get("large"),
        )

        result.append(face)

    if not result:
        image_uris = item.get("image_uris") or {}

        face = Card_Face(
            parent_id=oracle_id,
            mana_cost=item.get("mana_cost"),
            cmc=float(item.get("cmc") or 0),
            name=item.get("name"),
            oracle_text=item.get("oracle_text"),
            power=item.get("power"),
            toughness=item.get("toughness"),
            type_line=item.get("type_line"),
            small_image=image_uris.get("small"),
            normal_image=image_uris.get("normal"),
            large_image=image_uris.get("large"),
        )
        result.append(face)

    return result


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None

    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    return value


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    parsed = datetime.fromisoformat(value)
    return _normalize_datetime(parsed)
