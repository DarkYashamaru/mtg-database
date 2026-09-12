"""Run the exclusive MTG database download, import, and marker-refresh workflow."""
from __future__ import annotations

import fcntl
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database.create_database import create_database, vacuum_database
from scripts.download_all_data import download_from_scryfall
from scripts.import_all import import_data_to_database
from tools.logger import logger

MAINTENANCE_LOCK_PATH = BACKEND_DIR / "cards.sqlite.maintenance.lock"


@contextmanager
def exclusive_maintenance_lock() -> Iterator[None]:
    with MAINTENANCE_LOCK_PATH.open("a+") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("MTG database maintenance is already running.") from exc
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def refresh_mtg_data() -> None:
    with exclusive_maintenance_lock():
        logger.info("Starting exclusive MTG database maintenance...")
        create_database()
        logger.info("Checking Scryfall downloads...")
        download_from_scryfall()
        logger.info("Importing gameplay data and refreshing marker profiles...")
        import_data_to_database()
        logger.info("Vacuuming SQLite database...")
        vacuum_database()
        logger.info("MTG database maintenance complete.")


if __name__ == "__main__":
    refresh_mtg_data()
