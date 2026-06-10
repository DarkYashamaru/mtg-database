from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import requests


BULK_DATA_URL = "https://api.scryfall.com/bulk-data"
REQUEST_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "mtg-database/0.1",
}

ROOT_DIR = Path(__file__).resolve().parents[1]
SCRYFALL_DATA_DIR = ROOT_DIR / "downloads" / "scryfall"

REQUEST_TIMEOUT_SECONDS = 30
CHUNK_SIZE_BYTES = 1024 * 1024


class HttpSession(Protocol):
    def get(self, url: str, **kwargs: Any) -> requests.Response:
        """Subset of requests.Session used by this module."""


@dataclass(frozen=True)
class BulkDataFile:
    type: str
    updated_at: str
    download_uri: str
    size: int | None = None
    content_type: str | None = None
    content_encoding: str | None = None


@dataclass(frozen=True)
class BulkDataDownload:
    file_path: Path
    metadata_path: Path
    bulk_data: BulkDataFile
    downloaded: bool


class ScryfallBulkDataDownloader:

    def __init__(self, bulk_data_type: str, file_path: Path, metadata_path: Path, session: HttpSession | None = None) -> None:
        self.bulk_data_type = bulk_data_type
        self.file_path = file_path
        self.metadata_path = metadata_path
        self.session = session or requests.Session()

    def get_bulk_data(self) -> BulkDataFile:
        response = self.session.get(
            BULK_DATA_URL,
            headers=REQUEST_HEADERS,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        try:
            response.raise_for_status()

            payload = response.json()
            for item in payload.get("data", []):
                if item.get("type") == self.bulk_data_type:
                    return self._parse_bulk_data_file(item)
        finally:
            response.close()

        raise ValueError(
            f"Scryfall bulk-data response did not include {self.bulk_data_type}."
        )

    def download_if_needed(self) -> BulkDataDownload:
        bulk_data = self.get_bulk_data()

        if self._has_current_download(bulk_data):
            return BulkDataDownload(
                self.file_path,
                self.metadata_path,
                bulk_data,
                downloaded=False,
            )

        self._download_file(bulk_data.download_uri)
        self._write_metadata(bulk_data)

        return BulkDataDownload(
            self.file_path,
            self.metadata_path,
            bulk_data,
            downloaded=True,
        )

    def _parse_bulk_data_file(self, item: dict[str, Any]) -> BulkDataFile:
        try:
            return BulkDataFile(
                type=item["type"],
                updated_at=item["updated_at"],
                download_uri=item["download_uri"],
                size=item.get("size"),
                content_type=item.get("content_type"),
                content_encoding=item.get("content_encoding"),
            )
        except KeyError as error:
            raise ValueError(
                f"Scryfall bulk-data item is missing {error.args[0]!r}."
            ) from error

    def _has_current_download(self, bulk_data: BulkDataFile) -> bool:
        if not self.file_path.exists() or not self.metadata_path.exists():
            return False

        try:
            metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False

        return metadata.get("updated_at") == bulk_data.updated_at

    def _download_file(self, url: str) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.file_path.with_suffix(f"{self.file_path.suffix}.download")

        response = self.session.get(
            url,
            headers=REQUEST_HEADERS,
            stream=True,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        try:
            response.raise_for_status()
            with temporary_path.open("wb") as file:
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE_BYTES):
                    if chunk:
                        file.write(chunk)
        finally:
            response.close()

        temporary_path.replace(self.file_path)

    def _write_metadata(self, bulk_data: BulkDataFile) -> None:
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.metadata_path.with_suffix(
            f"{self.metadata_path.suffix}.download"
        )
        temporary_path.write_text(
            json.dumps(
                {
                    "type": bulk_data.type,
                    "updated_at": bulk_data.updated_at,
                    "download_uri": bulk_data.download_uri,
                    "size": bulk_data.size,
                    "content_type": bulk_data.content_type,
                    "content_encoding": bulk_data.content_encoding,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(self.metadata_path)
