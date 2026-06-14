from contextlib import asynccontextmanager
from collections import defaultdict
from collections.abc import Iterable

import uvicorn
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from database.create_database import create_database
from database.session import get_db

from models.card import (
    Card,
    Card_Face,
    Card_Keyword,
    Face_Subtypes,
    Face_Supertypes,
    Face_Types,
)
from models.color import Color_Identity
from models.public_schemas import CardSchema, card_to_schema
from models.tag import Tag, TagRelation, Tagging

from scripts.download_all_data import download_from_scryfall
from scripts.import_all import import_data_to_database
import re
from pydantic import BaseModel

class DecklistRequest(BaseModel):
    decklist: str


CARD_LOAD_OPTIONS = (
    selectinload(Card.taggings).selectinload(Tagging.tag),
    selectinload(Card.color_identity).selectinload(Color_Identity.color),
    selectinload(Card.keywords).selectinload(Card_Keyword.keyword),
    selectinload(Card.faces)
    .selectinload(Card_Face.supertypes)
    .selectinload(Face_Supertypes.type),
    selectinload(Card.faces)
    .selectinload(Card_Face.types)
    .selectinload(Face_Types.type),
    selectinload(Card.faces)
    .selectinload(Card_Face.subtypes)
    .selectinload(Face_Subtypes.type),
)


# --------------------------------------------------
# Startup / Shutdown
# --------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting MTG Database API...")

    create_database()

    # Uncomment ONLY when you want to refresh data
    download_data()
    import_data()

    print("Startup complete")

    yield

    print("Shutting down...")

app = FastAPI(
    title="MTG Database API",
    version="0.1.0",
    lifespan=lifespan,
)

def parse_decklist(decklist: str) -> list[str]:
    names = []

    for line in decklist.splitlines():
        line = line.strip()

        if not line:
            continue

        match = re.match(r"^\d+\s+(.+?)(?:\s+\([A-Z0-9]+\)\s+\d+)?$", line)

        if not match:
            raise ValueError(f"Invalid decklist line: {line}")

        names.append(match.group(1))

    return names


def load_inherited_tags_by_direct_id(
    db: Session,
    direct_tag_ids: Iterable[str],
) -> dict[str, list[Tag]]:
    requested_tag_ids = set(direct_tag_ids)

    if not requested_tag_ids:
        return {}

    tags_by_id = {
        tag.id: tag
        for tag in db.execute(select(Tag)).scalars()
    }
    parents_by_child: dict[str, list[str]] = defaultdict(list)

    for relation in db.execute(select(TagRelation)).scalars():
        parents_by_child[relation.child_id].append(relation.parent_id)

    ancestor_cache: dict[str, tuple[str, ...]] = {}

    def ancestor_ids(tag_id: str) -> tuple[str, ...]:
        if tag_id in ancestor_cache:
            return ancestor_cache[tag_id]

        ancestors: list[str] = []
        seen: set[str] = set()
        stack = list(parents_by_child.get(tag_id, []))

        while stack:
            parent_id = stack.pop()

            if parent_id in seen:
                continue

            seen.add(parent_id)
            ancestors.append(parent_id)
            stack.extend(parents_by_child.get(parent_id, []))

        ancestor_cache[tag_id] = tuple(ancestors)
        return ancestor_cache[tag_id]

    return {
        tag_id: [
            tags_by_id[ancestor_id]
            for ancestor_id in ancestor_ids(tag_id)
            if ancestor_id in tags_by_id
        ]
        for tag_id in requested_tag_ids
    }


def direct_tag_ids_for_cards(cards: Iterable[Card]) -> set[str]:
    return {
        tagging.tag_id
        for card in cards
        for tagging in card.taggings
    }


# --------------------------------------------------
# Router
# --------------------------------------------------

router = APIRouter(prefix="/api")


@router.get("/cards/id/{oracle_id}", response_model=CardSchema,)
def get_card(oracle_id: str, db: Session = Depends(get_db),):

    stmt = (
        select(Card)
        .options(*CARD_LOAD_OPTIONS)
        .where(Card.oracle_id == oracle_id)
    )

    card = db.execute(stmt).scalar_one_or_none()

    if card is None:
        raise HTTPException(
            status_code=404,
            detail="Card not found",
        )

    inherited_tags_by_direct_id = load_inherited_tags_by_direct_id(
        db,
        direct_tag_ids_for_cards([card]),
    )

    return card_to_schema(card, inherited_tags_by_direct_id)

@router.get("/cards/by-name", response_model=CardSchema,)
def get_card_by_name(name: str, db: Session = Depends(get_db),):

    stmt = (
        select(Card)
        .options(*CARD_LOAD_OPTIONS)
        .where(Card.name == name)
    )

    card = db.execute(stmt).scalar_one_or_none()

    if card is None:
        raise HTTPException(
            status_code=404,
            detail="Card not found",
        )

    inherited_tags_by_direct_id = load_inherited_tags_by_direct_id(
        db,
        direct_tag_ids_for_cards([card]),
    )

    return card_to_schema(card, inherited_tags_by_direct_id)

@router.post("/cards/bulk", response_model=list[CardSchema],)
def get_cards_bulk(request: DecklistRequest, db: Session = Depends(get_db),):

    try:
        names = parse_decklist(request.decklist)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    stmt = (
        select(Card)
        .options(*CARD_LOAD_OPTIONS)
        .where(Card.name.in_(names))
    )

    cards = db.execute(stmt).scalars().all()

    cards_by_name = {
        card.name: card
        for card in cards
    }

    missing = [
        name
        for name in names
        if name not in cards_by_name
    ]

    if missing:
        raise HTTPException(
            status_code=400,
            detail={
                "missing_cards": missing,
            },
        )

    inherited_tags_by_direct_id = load_inherited_tags_by_direct_id(
        db,
        direct_tag_ids_for_cards(cards),
    )

    return [
        card_to_schema(cards_by_name[name], inherited_tags_by_direct_id)
        for name in names
    ]


# Register router
app.include_router(router)


# --------------------------------------------------
# Data management helpers
# --------------------------------------------------

def download_data():
    print("Downloading bulk data from Scryfall...")
    download_from_scryfall()
    print("Download complete")


def import_data():
    print("Importing data into database...")
    import_data_to_database()
    print("Import complete")


# --------------------------------------------------
# Local development entrypoint
# --------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=20011,
        reload=True,
    )
