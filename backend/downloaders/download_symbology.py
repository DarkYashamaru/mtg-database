from __future__ import annotations

import json

import requests

from downloaders.scryfall_bulk_data import SCRYFALL_DATA_DIR
from downloaders.scryfall_download_utility import BASE_URL, REQUEST_HEADERS

SYMBOLS_PATH = SCRYFALL_DATA_DIR / "symbology.json"


def download_symbology() -> None:
    response = requests.get(f"{BASE_URL}/symbology", headers=REQUEST_HEADERS, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload.get("data"), list):
        raise ValueError("Invalid Scryfall symbology response.")
    SYMBOLS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = SYMBOLS_PATH.with_suffix(".json.download")
    temporary.write_text(json.dumps(payload), encoding="utf-8")
    temporary.replace(SYMBOLS_PATH)
