from __future__ import annotations

from downloaders.scryfall_bulk_data import (  # noqa: E402
    SCRYFALL_DATA_DIR,
    BulkDataDownload,
    BulkDataFile,
    HttpSession,
    ScryfallBulkDataDownloader,
)

ORACLE_TAGS_TYPE = "oracle_tags"
ORACLE_TAGS_PATH = SCRYFALL_DATA_DIR / "oracle_tags.jsonl.gz"
ORACLE_TAGS_METADATA_PATH = SCRYFALL_DATA_DIR / "oracle_tags.meta.json"

def create_oracle_tags_downloader(session: HttpSession | None = None,) -> ScryfallBulkDataDownloader:

    return ScryfallBulkDataDownloader(
        bulk_data_type=ORACLE_TAGS_TYPE,
        file_path=ORACLE_TAGS_PATH,
        metadata_path=ORACLE_TAGS_METADATA_PATH,
        session=session,
    )


def get_oracle_tags_bulk_data(session: HttpSession | None = None) -> BulkDataFile:
    return create_oracle_tags_downloader(session).get_bulk_data()


def download_oracle_tags_if_needed(session: HttpSession | None = None,) -> BulkDataDownload:    
    return create_oracle_tags_downloader(session).download_if_needed()
