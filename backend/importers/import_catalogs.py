# downloaders/download_catalogs.py
from __future__ import annotations

import requests
from sqlalchemy import delete
from sqlalchemy.orm import Session
from database.session import session_scope
from downloaders.scryfall_download_utility import BASE_URL, REQUEST_HEADERS

from models.catalogs import (
    Supertype,
    CardType,
    ArtifactType,
    BattleType,
    CreatureType,
    EnchantmentType,
    LandType,
    PlaneswalkerType,
    SpellType,
    Power,
    Toughness,
    Loyalty,
    KeywordAbility,
    KeywordAction,
    AbilityWord,
    Subtype
)

CATALOG_SOURCES = [
    ("/catalog/supertypes", Supertype),
    ("/catalog/card-types", CardType),
    ("/catalog/artifact-types", ArtifactType),
    ("/catalog/battle-types", BattleType),
    ("/catalog/creature-types", CreatureType),
    ("/catalog/enchantment-types", EnchantmentType),
    ("/catalog/land-types", LandType),
    ("/catalog/planeswalker-types", PlaneswalkerType),
    ("/catalog/spell-types", SpellType),
    ("/catalog/powers", Power),
    ("/catalog/toughnesses", Toughness),
    ("/catalog/loyalties", Loyalty),
    ("/catalog/keyword-abilities", KeywordAbility),
    ("/catalog/keyword-actions", KeywordAction),
    ("/catalog/ability-words", AbilityWord),
]

SUBTYPES_SOURCES = [
    "/catalog/artifact-types",
    "/catalog/battle-types",
    "/catalog/creature-types",
    "/catalog/enchantment-types",
    "/catalog/land-types",
    "/catalog/planeswalker-types",
    "/catalog/spell-types",
]



def download_catalog(endpoint: str, model: type) -> None:
    response = requests.get(f"{BASE_URL}{endpoint}", headers=REQUEST_HEADERS, timeout=30)
    response.raise_for_status()

    payload = response.json()
    values = payload["data"]

    with session_scope() as session:
        existing = {
            row.value
            for row in session.query(model).all()
        }

        new_values = [
            model(value=v)
            for v in values
            if v not in existing
        ]

        session.add_all(new_values)

def download_subtypes():

    all_types = []

    for endpoint in SUBTYPES_SOURCES:

        response = requests.get(f"{BASE_URL}{endpoint}", headers=REQUEST_HEADERS, timeout=30)
        response.raise_for_status()

        payload = response.json()
        values = payload["data"]

        for v in values:
            all_types.append(v)

    
    with session_scope() as session:

        for type in all_types:
            subtype = Subtype(value=type)
            session.merge(subtype)

def download_all_catalogs() -> None:
    for endpoint, model in CATALOG_SOURCES:
        download_catalog(endpoint, model)

    download_subtypes()