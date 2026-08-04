from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any


def load_scryfall_bulk_items(source_path: Path) -> list[dict[str, Any]]:
    if source_path.suffixes[-2:] == [".jsonl", ".gz"]:
        with gzip.open(source_path, mode="rt", encoding="utf-8") as file:
            return [json.loads(line) for line in file if line.strip()]

    with source_path.open(encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, list):
        raise ValueError(f"Expected a JSON array in {source_path}.")

    return payload
