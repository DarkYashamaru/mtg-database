from __future__ import annotations

from downloaders.scryfall_bulk_data import (
    SCRYFALL_DATA_DIR,
    BulkDataDownload,
    HttpSession,
    ScryfallBulkDataDownloader,
)

DEFAULT_CARDS_TYPE = "default_cards"
DEFAULT_CARDS_PATH = SCRYFALL_DATA_DIR / "default_cards.jsonl.gz"
DEFAULT_CARDS_METADATA_PATH = SCRYFALL_DATA_DIR / "default_cards.meta.json"


def download_default_cards_if_needed(
    session: HttpSession | None = None,
) -> BulkDataDownload:
    return ScryfallBulkDataDownloader(
        bulk_data_type=DEFAULT_CARDS_TYPE,
        file_path=DEFAULT_CARDS_PATH,
        metadata_path=DEFAULT_CARDS_METADATA_PATH,
        session=session,
    ).download_if_needed()
