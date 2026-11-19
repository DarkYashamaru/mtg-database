from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select

from database.session import session_scope
from downloaders.download_default_cards import DEFAULT_CARDS_PATH
from importers.scryfall_bulk_reader import load_scryfall_bulk_items
from models.card import Card
from models.printing import (
    CardPrinting,
    PrintingFace,
    PrintingFaceUri,
    PrintingLegality,
    PrintingPart,
    PrintingUri,
    PrintingValue,
)


SCALAR_FIELDS = (
    "arena_id", "lang", "mtgo_id", "mtgo_foil_id", "resource_id", "tcgplayer_id",
    "tcgplayer_etched_id", "cardmarket_id", "object", "layout", "name", "cmc",
    "defense", "edhrec_rank", "game_changer", "hand_modifier", "life_modifier",
    "loyalty", "mana_cost", "oracle_text", "penny_rank", "power", "reserved",
    "toughness", "type_line", "artist", "booster", "border_color", "card_back_id",
    "collector_number", "content_warning", "digital", "flavor_name", "flavor_text",
    "frame", "full_art", "highres_image", "illustration_id", "image_status", "oversized",
    "printed_name", "printed_text", "printed_type_line", "promo", "rarity", "reprint",
    "set_id", "set_name", "set_type", "story_spotlight", "textless", "variation",
    "variation_of", "security_stamp", "watermark",
)
ARRAY_FIELDS = (
    "multiverse_ids", "artist_ids", "attraction_lights", "finishes", "frame_effects",
    "games", "keywords", "promo_types", "colors", "color_indicator", "produced_mana",
)
URI_FIELDS = ("image_uris", "prices", "purchase_uris", "related_uris")


def _date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _printing(item: dict[str, Any], known_oracle_ids: set[str]) -> CardPrinting | None:
    printing_id = item.get("id")
    if not isinstance(printing_id, str):
        return None
    values = {field: item.get(field) for field in SCALAR_FIELDS}
    values["id"] = printing_id
    values["oracle_id"] = item.get("oracle_id") if item.get("oracle_id") in known_oracle_ids else None
    values["cmc"] = float(item.get("cmc") or 0)
    values["color_identity_text"] = "".join(item.get("color_identity") or [])
    values["set_code"] = item.get("set") or ""
    values["released_at"] = _date(item.get("released_at"))
    preview = item.get("preview") or {}
    values["previewed_at"] = _date(preview.get("previewed_at"))
    values["preview_source"] = preview.get("source")
    values["preview_source_uri"] = preview.get("source_uri")
    return CardPrinting(**values)


def import_default_card_printings(source_path: Path = DEFAULT_CARDS_PATH) -> int:
    if not source_path.exists():
        raise FileNotFoundError(f"Default cards bulk file not found at {source_path}.")
    payload = load_scryfall_bulk_items(source_path)
    with session_scope() as session:
        known_oracle_ids = set(session.scalars(select(Card.oracle_id)).all())
        session.execute(delete(PrintingFaceUri))
        session.execute(delete(PrintingFace))
        session.execute(delete(PrintingValue))
        session.execute(delete(PrintingUri))
        session.execute(delete(PrintingLegality))
        session.execute(delete(PrintingPart))
        session.execute(delete(CardPrinting))

        count = 0
        for item in payload:
            printing = _printing(item, known_oracle_ids)
            if printing is None:
                continue
            session.add(printing)
            printing_id = printing.id
            for field in ARRAY_FIELDS:
                for position, value in enumerate(item.get(field) or []):
                    session.add(PrintingValue(printing_id=printing_id, field=field, value=str(value), position=position))
            for group in URI_FIELDS:
                for key, uri in (item.get(group) or {}).items():
                    session.add(PrintingUri(printing_id=printing_id, group=group, key=key, uri=str(uri)))
            for format_name, status in (item.get("legalities") or {}).items():
                session.add(PrintingLegality(printing_id=printing_id, format=format_name, status=status))
            for part in item.get("all_parts") or []:
                session.add(PrintingPart(printing_id=printing_id, related_id=part["id"], component=part["component"], name=part["name"], type_line=part["type_line"], uri=part["uri"]))
            for index, face_data in enumerate(item.get("card_faces") or []):
                face = PrintingFace(
                    printing_id=printing_id, face_index=index, artist=face_data.get("artist"), artist_id=face_data.get("artist_id"), cmc=face_data.get("cmc"), color_indicator_text="".join(face_data.get("color_indicator") or []), colors_text="".join(face_data.get("colors") or []), defense=face_data.get("defense"), flavor_text=face_data.get("flavor_text"), illustration_id=face_data.get("illustration_id"), layout=face_data.get("layout"), loyalty=face_data.get("loyalty"), mana_cost=face_data.get("mana_cost"), name=face_data.get("name") or "", object=face_data.get("object") or "card_face", oracle_id=face_data.get("oracle_id"), oracle_text=face_data.get("oracle_text"), power=face_data.get("power"), printed_name=face_data.get("printed_name"), printed_text=face_data.get("printed_text"), printed_type_line=face_data.get("printed_type_line"), toughness=face_data.get("toughness"), type_line=face_data.get("type_line"), watermark=face_data.get("watermark"),
                )
                session.add(face)
                for key, uri in (face_data.get("image_uris") or {}).items():
                    session.add(PrintingFaceUri(printing_id=printing_id, face_index=index, key=key, uri=str(uri)))
            count += 1
        return count
