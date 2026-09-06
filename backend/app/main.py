from contextlib import asynccontextmanager
from collections import defaultdict
from collections.abc import Iterable
import uvicorn
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query
from sqlalchemy import func, select, exists, not_, or_, distinct
from sqlalchemy.orm import Session, selectinload, joinedload
from database.create_database import create_database
from database.session import get_db
from pydantic import BaseModel, Field
from typing import Optional, List
from models.card import *
from models.archetype import *
from models.color import *
from models.marker import *
from models.public_schemas import *
from models.tag import *
from models.category import *
from models.themes import *
from scripts.download_all_data import download_from_scryfall
from scripts.import_all import import_data_to_database
import re
from pydantic import BaseModel
from scripts.precompute_card_theme_edhrec import precompute_card_theme_from_edhrec
from scripts.precompute_commander_theme_edhrec import precompute_commander_theme_edhrec
from tools.logger import logger
from services.decklist_resolver import resolve_decklist_cards
from services.bulk_card_lookup import load_cards_by_oracle_ids
from services.commander_validation import validate_commander_selection
from services.search_filters import (
    card_cmc_match_clauses,
    card_tag_match_clause,
    card_type_match_clause,
    parse_search_terms,
    parse_tag_search_terms,
    resolve_tag_ids,
)
from app.commander_validation_schemas import CommanderValidationRequest

class DecklistRequest(BaseModel):
    decklist: str


class OracleIdsRequest(BaseModel):
    oracle_ids: list[str] = Field(default_factory=list)


CARD_LOAD_OPTIONS = (
    selectinload(Card.taggings).selectinload(Tagging.tag),
    selectinload(Card.card_markers).selectinload(CardMarker.marker),
    selectinload(Card.markers),
    selectinload(Card.color_identity).selectinload(Color_Identity.color),
    selectinload(Card.produced_mana).selectinload(CardProducedMana.color),
    selectinload(Card.keywords).selectinload(Card_Keyword.keyword),
    selectinload(Card.categories),
    selectinload(Card.archetypes),
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
    logger.info("Starting MTG Database API...")

    create_database()

    # Uncomment ONLY when you want to refresh data
    download_data()
    import_data()

    db: Session = next(get_db())

    # try:

    #     precompute_card_theme_from_edhrec(db)
    #     precompute_commander_theme_edhrec(db)
    
    # except:
    #     logger.exception("EDHREC imports failed")

    logger.info("Startup complete")

    yield

    logger.info("Shutting down...")

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

def card_to_full_schema(card: Card, db: Session) -> CardSchema:
    inherited_tags_by_direct_id = load_inherited_tags_by_direct_id(
        db,
        direct_tag_ids_for_cards([card]),
    )

    oracle_ids = [card.oracle_id] if card.oracle_id else []
    themes_map = get_themes_for_cards_map(oracle_ids, db) if oracle_ids else {}

    return card_to_schema(card, inherited_tags_by_direct_id, themes_map)


def commanders_stmt():
    return (
        select(Card)
        .options(*CARD_LOAD_OPTIONS)
        .where(
            or_(
                exists(
                    select(1)
                    .select_from(Card_Face)
                    .where(
                        Card_Face.parent_id == Card.oracle_id,
                        Card_Face.type_line.ilike("%Legendary%Creature%"),
                    )
                ),
                exists(
                    select(1)
                    .select_from(Card_Face)
                    .where(
                        Card_Face.parent_id == Card.oracle_id,
                        Card_Face.oracle_text.ilike("%can be your commander%"),
                    )
                ),
            )
        )
        .order_by(Card.name)
        .distinct()
    )


@router.get("/cards/id/{oracle_id}", response_model=CardSchema)
def get_card(oracle_id: str, db: Session = Depends(get_db)):
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

    return card_to_full_schema(card, db)

@router.get("/cards/by-name", response_model=CardSchema)
def get_card_by_name(name: str, db: Session = Depends(get_db)):
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

    return card_to_full_schema(card, db)


@router.get("/commanders", response_model=list[CardSchema])
def get_commanders(db: Session = Depends(get_db)):
    cards = db.execute(commanders_stmt()).scalars().all()

    inherited_tags_by_direct_id = load_inherited_tags_by_direct_id(
        db,
        direct_tag_ids_for_cards(cards),
    )

    oracle_ids = [card.oracle_id for card in cards if card.oracle_id]
    themes_map = get_themes_for_cards_map(oracle_ids, db) if oracle_ids else {}

    return [
        card_to_schema(card, inherited_tags_by_direct_id, themes_map)
        for card in cards
    ]


@router.post("/commanders/validate")
def validate_commanders(request: CommanderValidationRequest, db: Session = Depends(get_db)):
    oracle_ids = {
        oracle_id
        for selection in request.selections
        for oracle_id in selection.oracle_ids
    }
    cards = db.execute(
        select(Card)
        .options(*CARD_LOAD_OPTIONS)
        .where(Card.oracle_id.in_(oracle_ids))
    ).scalars().all() if oracle_ids else []
    cards_by_oracle_id = {card.oracle_id: card for card in cards}

    return {
        "results": [
            {
                "oracle_ids": result.oracle_ids,
                "valid": result.valid,
                "code": result.code,
                "message": result.message,
            }
            for result in (
                validate_commander_selection(cards_by_oracle_id, selection.oracle_ids)
                for selection in request.selections
            )
        ]
    }



def get_themes_for_cards_map(oracle_ids: list[str], db) -> dict[str, list[CardThemeMinimalSchema]]:

    stmt = (
        select(CardTheme.oracle_id, CardTheme.theme_id, CardTheme.score, Theme.name, Theme.curated)
        .join(Theme, CardTheme.theme_id == Theme.id)
        .where(CardTheme.oracle_id.in_(oracle_ids))
    )
    results = db.execute(stmt).all()
    
    theme_map = {}
    for row in results:
        if row.oracle_id not in theme_map:
            theme_map[row.oracle_id] = []
        theme_map[row.oracle_id].append(
            CardThemeMinimalSchema(
                theme_id=row.theme_id,
                name=row.name,
                curated=row.curated,
                score=row.score
            )
        )
    return theme_map

@router.post("/cards/bulk", response_model=list[CardSchema])
def get_cards_bulk(request: DecklistRequest, db: Session = Depends(get_db)):
    try:
        names = parse_decklist(request.decklist)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    stmt = (
        select(Card)
        .options(*CARD_LOAD_OPTIONS)
        .where(Card.name.in_(names))
    )
    cards = db.execute(stmt).scalars().all()

    cards_by_name = {card.name: card for card in cards}
    missing = [name for name in names if name not in cards_by_name]

    if missing:
        raise HTTPException(
            status_code=400,
            detail={"missing_cards": missing},
        )

    # 1. Extract unique oracle IDs from the found cards
    oracle_ids = list({card.oracle_id for card in cards if card.oracle_id})

    # 2. Batch-fetch the themes map in a single query
    themes_map = get_themes_for_cards_map(oracle_ids, db)

    # Existing logic for inherited tags
    inherited_tags_by_direct_id = load_inherited_tags_by_direct_id(
        db,
        direct_tag_ids_for_cards(cards),
    )

    # 3. Pass the themes_map into your schema mapping engine
    return [
        card_to_schema(cards_by_name[name], inherited_tags_by_direct_id, themes_map)
        for name in names
    ]


@router.post("/cards/bulk-by-id", response_model=list[CardSchema])
def get_cards_bulk_by_id(request: OracleIdsRequest, db: Session = Depends(get_db)):
    try:
        cards, missing_oracle_ids = load_cards_by_oracle_ids(
            db,
            request.oracle_ids,
            load_options=CARD_LOAD_OPTIONS,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "invalid_oracle_ids",
                "message": str(exc),
            },
        ) from exc

    if missing_oracle_ids:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "missing_oracle_ids",
                "missing_oracle_ids": missing_oracle_ids,
            },
        )

    oracle_ids = [card.oracle_id for card in cards]
    themes_map = get_themes_for_cards_map(oracle_ids, db)
    inherited_tags_by_direct_id = load_inherited_tags_by_direct_id(
        db,
        direct_tag_ids_for_cards(cards),
    )
    return [
        card_to_schema(card, inherited_tags_by_direct_id, themes_map)
        for card in cards
    ]


@router.post("/cards/bulk-resolve")
def resolve_cards_bulk(request: DecklistRequest, db: Session = Depends(get_db)):
    try:
        names = parse_decklist(request.decklist)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    resolved_cards, warnings = resolve_decklist_cards(names, db, CARD_LOAD_OPTIONS)
    cards = [card for _, card in resolved_cards]
    oracle_ids = list({card.oracle_id for card in cards if card.oracle_id})
    themes_map = get_themes_for_cards_map(oracle_ids, db)
    inherited_tags_by_direct_id = load_inherited_tags_by_direct_id(
        db,
        direct_tag_ids_for_cards(cards),
    )

    return {
        "cards": [
            {
                "requested_name": requested_name,
                "card": card_to_schema(card, inherited_tags_by_direct_id, themes_map),
            }
            for requested_name, card in resolved_cards
        ],
        "warnings": warnings,
    }

@router.get("/tags", response_model=list[TagSchema])
def get_all_tags(db: Session = Depends(get_db)):
    stmt = select(Tag)

    tags = db.execute(stmt).scalars().all()

    return [tag_to_schema(tag) for tag in tags]


@router.get("/categories", response_model=list[CategorySchema])
def get_all_categories(db: Session = Depends(get_db)):
    stmt = select(Category).order_by(Category.name)

    categories = db.execute(stmt).scalars().all()

    return [category_to_schema(category) for category in categories]


@router.get("/archetypes", response_model=list[ArchetypeSchema])
def get_all_archetypes(db: Session = Depends(get_db)):
    stmt = select(Archetype).order_by(Archetype.name)

    archetypes = db.execute(stmt).scalars().all()

    return [archetype_to_schema(archetype) for archetype in archetypes]


@router.get("/themes", response_model=list[ThemeSummarySchema])
def get_all_themes(db: Session = Depends(get_db)):
    themes = db.scalars(select(Theme).order_by(Theme.name, Theme.id)).all()
    return [
        ThemeSummarySchema(id=theme.id, name=theme.name, curated=bool(theme.curated))
        for theme in themes
    ]


@router.get("/themes/id/{archetype_id}", response_model=ThemeypeSchema,)
def get_archetype(archetype_id: int, db: Session = Depends(get_db),):

    stmt = (
        select(Theme)
        .options(*THEME_LOAD_OPTIONS)
        .where(Theme.id == archetype_id)
    )

    archetype = db.execute(stmt).scalar_one_or_none()

    if archetype is None:
        raise HTTPException(
            status_code=404,
            detail="Archetype not found",
        )

    return theme_to_schema(archetype)

@router.get("/themes/by-name", response_model=ThemeypeSchema,)
def get_archetype_by_name(name: str, db: Session = Depends(get_db),):

    stmt = (
        select(Theme)
        .options(*THEME_LOAD_OPTIONS)
        .where(Theme.name == name)
    )

    archetype = db.execute(stmt).scalar_one_or_none()

    if archetype is None:
        raise HTTPException(
            status_code=404,
            detail="Archetype not found",
        )

    return theme_to_schema(archetype)


@router.get("/themes/by-commander/{oracle_id}", response_model=list[CommanderThemeSchema])
def get_theme_by_card(oracle_id: str, db: Session = Depends(get_db)):
    # 1. Select properties explicitly across both tables
    stmt = (
        select(
            CommanderTheme.oracle_id,
            CommanderTheme.theme_id,
            CommanderTheme.score,
            Theme.name,
            Theme.curated
        )
        .join(Theme, CommanderTheme.theme_id == Theme.id) # Join tracking foreign keys
        .where(CommanderTheme.oracle_id == oracle_id)
    )

    # 2. Fetch the flat data tuples
    results = db.execute(stmt).all()

    # 3. Map the dataset entries straight into the revised response schema list
    return [
        CommanderThemeSchema(
            oracle_id=row.oracle_id,
            theme_id=row.theme_id,
            score=row.score,
            name=row.name,
            curated=row.curated
        )
        for row in results
    ]

class SearchOptions(BaseModel):
    name: Optional[str] = Field(None, description="Partial name match")
    colors: Optional[List[str]] = Field(None, description="Color symbols, e.g. ['W', 'U']")
    exact_colors: bool = Field(False, description="Match exact color identity")

    tags: Optional[List[str]] = Field(None, description="Included tags")
    cmc_min: Optional[float] = Field(None, ge=0, description="Minimum mana value")
    cmc_max: Optional[float] = Field(None, ge=0, description="Maximum mana value")
    exclude_tags: Optional[List[str]] = Field(None, description="Excluded tags")
    markers: Optional[List[str]] = Field(None, description="Included markers")
    exclude_markers: Optional[List[str]] = Field(None, description="Excluded markers")

    card_type: Optional[str] = Field(
        None,
        description="Comma-separated type line terms that must match one face",
    )

    oracle_text: Optional[List[str]] = Field(None, description="Included oracle text terms")
    exclude_oracle_text: Optional[List[str]] = Field(None, description="Excluded oracle text terms")

@router.get("/advanced/", response_model=list[CardSchema])
def advanced_search(
    name: str | None = None,
    colors: list[str] = Query(default_factory=list),
    exact_colors: bool = False,
    cmc_min: float | None = Query(default=None, ge=0),
    cmc_max: float | None = Query(default=None, ge=0),
    colorless: bool = False,

    tags: list[str] = Query(default_factory=list),
    exclude_tags: list[str] = Query(default_factory=list),
    markers: list[str] = Query(default_factory=list),
    exclude_markers: list[str] = Query(default_factory=list),

    card_type: str | None = None,

    oracle_text: list[str] = Query(default_factory=list),
    exclude_oracle_text: list[str] = Query(default_factory=list),

    db: Session = Depends(get_db),
):
     
    logger.info(f"Advanced Search: name: {name}\ncolors: {colors}\nexact_colors: {exact_colors}\ncolorless: {colorless}\ntags:{tags}\nexclude_tags: {exclude_tags}\nmarkers:{markers}\nexclude_markers: {exclude_markers}\ncard_type: {card_type}\noracle_text: {oracle_text}\nexclude_oracle_text: {exclude_oracle_text}")

    if cmc_min is not None and cmc_max is not None and cmc_min > cmc_max:
        raise HTTPException(
            status_code=400,
            detail="cmc_min cannot be greater than cmc_max",
        )

    stmt = select(Card).options(*CARD_LOAD_OPTIONS)

    for cmc_clause in card_cmc_match_clauses(cmc_min, cmc_max):
        stmt = stmt.where(cmc_clause)

    if name:
        stmt = stmt.where(Card.name.ilike(f"%{name}%"))

    # Parse inputs to isolate quoted text phrases from basic comma splits
    parsed_oracle_text = parse_search_terms(oracle_text)
    parsed_exclude_oracle_text = parse_search_terms(exclude_oracle_text)

    # Each phrase/word in this list gets executed as an AND statement
    for text in parsed_oracle_text:
        stmt = stmt.where(
            exists(
                select(1)
                .select_from(Card_Face)
                .where(
                    Card_Face.parent_id == Card.oracle_id,
                    Card_Face.oracle_text.ilike(f"%{text}%"),
                )
            )
        )

    for text in parsed_exclude_oracle_text:
        stmt = stmt.where(
            ~exists(
                select(1)
                .select_from(Card_Face)
                .where(
                    Card_Face.parent_id == Card.oracle_id,
                    Card_Face.oracle_text.ilike(f"%{text}%"),
                )
            )
        )

    if card_type:
        card_type_clause = card_type_match_clause(card_type)
        if card_type_clause is not None:
            stmt = stmt.where(card_type_clause)

    for tag_term in parse_tag_search_terms(tags):
        stmt = stmt.where(card_tag_match_clause(resolve_tag_ids(db, tag_term)))

    for tag_term in parse_tag_search_terms(exclude_tags):
        stmt = stmt.where(~card_tag_match_clause(resolve_tag_ids(db, tag_term)))

    for marker_value in markers:
        stmt = stmt.where(
            exists(
                select(1)
                .select_from(CardMarker)
                .join(Marker, CardMarker.marker_id == Marker.id)
                .where(
                    CardMarker.oracle_id == Card.oracle_id,
                    or_(
                        Marker.id == marker_value,
                        Marker.name == marker_value,
                    ),
                )
            )
        )

    for marker_value in exclude_markers:
        stmt = stmt.where(
            ~exists(
                select(1)
                .select_from(CardMarker)
                .join(Marker, CardMarker.marker_id == Marker.id)
                .where(
                    CardMarker.oracle_id == Card.oracle_id,
                    or_(
                        Marker.id == marker_value,
                        Marker.name == marker_value,
                    ),
                )
            )
        )

    if colors:
        allowed = {c.upper() for c in colors}
        valid = {"W", "U", "B", "R", "G"}

        invalid = allowed - valid
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid color(s): {sorted(invalid)}",
            )

        forbidden = valid - allowed

        if forbidden:
            stmt = stmt.where(
                ~exists(
                    select(1)
                    .select_from(Color_Identity)
                    .join(Color, Color_Identity.color_id == Color.id)
                    .where(
                        Color_Identity.card_id == Card.oracle_id,
                        Color.symbol.in_(list(forbidden)),
                    )
                )
            )

        if exact_colors:
            stmt = stmt.where(
                exists(
                    select(1)
                    .select_from(Color_Identity)
                    .join(Color, Color_Identity.color_id == Color.id)
                    .where(Color_Identity.card_id == Card.oracle_id)
                    .group_by(Color_Identity.card_id)
                    .having(func.count(distinct(Color.symbol)) == len(allowed))
                )
            )

    if colorless:
        stmt = stmt.where(
            exists(
                select(1)
                .select_from(Card_Face)
                .where(
                    Card_Face.parent_id == Card.oracle_id,
                    Card_Face.mana_cost.is_not(None),
                    Card_Face.mana_cost != "",
                )
            )
        )
        stmt = stmt.where(
            ~exists(
                select(1)
                .select_from(Card_Face)
                .where(
                    Card_Face.parent_id == Card.oracle_id,
                    Card_Face.mana_cost.is_not(None),
                    or_(
                        Card_Face.mana_cost.ilike("%W%"),
                        Card_Face.mana_cost.ilike("%U%"),
                        Card_Face.mana_cost.ilike("%B%"),
                        Card_Face.mana_cost.ilike("%R%"),
                        Card_Face.mana_cost.ilike("%G%"),
                    ),
                )
            )
        )

    cards = db.execute(stmt.distinct()).scalars().all()

    inherited_tags_by_direct_id = load_inherited_tags_by_direct_id(
        db,
        direct_tag_ids_for_cards(cards),
    )

    oracle_ids = list({card.oracle_id for card in cards if card.oracle_id})
    themes_map = get_themes_for_cards_map(oracle_ids, db) if oracle_ids else {}

    return [
        card_to_schema(card, inherited_tags_by_direct_id, themes_map)
        for card in cards
    ]


@router.get("/markers", response_model=list[MarkerSchema])
def get_all_markers(db: Session = Depends(get_db)):
    stmt = select(Marker).order_by(Marker.name)

    markers = db.execute(stmt).scalars().all()

    return [marker_to_schema(marker) for marker in markers]


@router.get("/markers/{marker_id}/cards", response_model=list[CardSchema])
def get_cards_for_marker(marker_id: str, db: Session = Depends(get_db)):
    marker = db.execute(
        select(Marker).where(Marker.id == marker_id)
    ).scalar_one_or_none()

    if marker is None:
        raise HTTPException(
            status_code=404,
            detail="Marker not found",
        )

    stmt = (
        select(Card)
        .options(*CARD_LOAD_OPTIONS)
        .join(CardMarker, CardMarker.oracle_id == Card.oracle_id)
        .where(CardMarker.marker_id == marker_id)
        .order_by(Card.name)
        .distinct()
    )
    cards = db.execute(stmt).scalars().all()

    inherited_tags_by_direct_id = load_inherited_tags_by_direct_id(
        db,
        direct_tag_ids_for_cards(cards),
    )

    oracle_ids = [card.oracle_id for card in cards if card.oracle_id]
    themes_map = get_themes_for_cards_map(oracle_ids, db) if oracle_ids else {}

    return [
        card_to_schema(card, inherited_tags_by_direct_id, themes_map)
        for card in cards
    ]

# @router.get("/categories", response_model=list[CategorySchema])
# def get_categories(db: Session = Depends(get_db)):

#     stmt = select(Category)

#     categories = db.execute(stmt).scalars().all()

#     return [category_to_schema(category) for category in categories]


# Register router
app.include_router(router)


# --------------------------------------------------
# Data management helpers
# --------------------------------------------------

def download_data():
    logger.info("Downloading bulk data from Scryfall...")
    download_from_scryfall()
    logger.info("Download complete")


def import_data():
    logger.info("Importing data into database...")
    import_data_to_database()
    logger.info("Import complete")


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
