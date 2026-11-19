from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from downloaders.scryfall_bulk_data import SCRYFALL_DATA_DIR
from downloaders.scryfall_download_utility import BASE_URL, REQUEST_HEADERS


CATALOG_NAMES = (
    "card-names",
    "artist-names",
    "word-bank",
    "supertypes",
    "card-types",
    "artifact-types",
    "battle-types",
    "creature-types",
    "enchantment-types",
    "land-types",
    "planeswalker-types",
    "spell-types",
    "powers",
    "toughnesses",
    "loyalties",
    "keyword-abilities",
    "keyword-actions",
    "ability-words",
    "flavor-words",
    "watermarks",
)

CATALOGS_DIRECTORY = SCRYFALL_DATA_DIR / "catalogs"
CATALOG_MANIFEST_PATH = CATALOGS_DIRECTORY / "manifest.json"


def _write_json_atomically(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.download")
    temporary_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)


def download_all_catalog_files() -> dict[str, dict[str, Any]]:
    """Fetch and archive every documented Scryfall Catalog response."""
    downloaded_at = datetime.now(timezone.utc).isoformat()
    manifest_catalogs: dict[str, dict[str, Any]] = {}

    for name in CATALOG_NAMES:
        response = requests.get(
            f"{BASE_URL}/catalog/{name}",
            headers=REQUEST_HEADERS,
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()

        if payload.get("object") != "catalog" or not isinstance(payload.get("data"), list):
            raise ValueError(f"Scryfall catalog {name!r} returned an invalid payload.")

        _write_json_atomically(CATALOGS_DIRECTORY / f"{name}.json", payload)
        manifest_catalogs[name] = {
            "uri": payload.get("uri"),
            "total_values": payload.get("total_values"),
            "downloaded_at": downloaded_at,
        }

    manifest = {
        "catalog_count": len(CATALOG_NAMES),
        "downloaded_at": downloaded_at,
        "catalogs": manifest_catalogs,
    }
    _write_json_atomically(CATALOG_MANIFEST_PATH, manifest)
    return manifest_catalogs
