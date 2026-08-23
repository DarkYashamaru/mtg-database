"""Populate each card's EDHREC Commander-deck adoption counts.

By default, only cards missing EDHREC counts are processed, making this script
safe to re-run. Use --force to refresh all cards.

Examples:
    python precompute_card_edhrec.py
    python precompute_card_edhrec.py --force
    python precompute_card_edhrec.py --rps 2
    python precompute_card_edhrec.py --limit 100
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
import random
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import requests
from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from database.create_database import create_database
from database.session import get_db
from models.card import Card

# Required so SQLAlchemy can resolve Card relationships that reference
# "Color_Identity" by class name during mapper configuration.
from models.color import Color_Identity  # noqa: F401

from tools.card_to_slug import card_name_to_slug, get_primary_card_name
from tools.logger import logger


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_REQUESTS_PER_SECOND = 4.0
DEFAULT_WORKERS = 4

COMMIT_EVERY = 100

REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

# Don't hammer the server again immediately after a 429.
MIN_RATE_LIMIT_BACKOFF = 60.0

# A single 403 may be caused by a strange/missing card route.
# Multiple consecutive 403s are much stronger evidence that access
# is actually being blocked.
MAX_CONSECUTIVE_403 = 5


# ---------------------------------------------------------------------------
# EDHREC-specific slug exceptions
# ---------------------------------------------------------------------------

EDHREC_SLUG_OVERRIDES: dict[str, str] = {
    '"Name Sticker" Goblin': "_____-goblin",
}


def get_edhrec_slug(card_name: str) -> str:
    """Return the slug EDHREC uses for a card."""

    primary_name = get_primary_card_name(card_name)

    override = EDHREC_SLUG_OVERRIDES.get(primary_name)

    if override is not None:
        logger.info(
            f"Using EDHREC slug override: "
            f"{primary_name} -> {override}"
        )
        return override

    return card_name_to_slug(primary_name)


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass
class EDHRECResult:
    oracle_id: str
    name: str
    num_decks: int | None = None
    potential_decks: int | None = None
    error: str | None = None
    fatal: bool = False

    @property
    def success(self) -> bool:
        return (
            self.error is None
            and self.num_decks is not None
            and self.potential_decks is not None
        )


# ---------------------------------------------------------------------------
# Global request rate limiter
# ---------------------------------------------------------------------------

class RequestRateLimiter:
    """Limit request starts globally across all worker threads."""

    def __init__(self, requests_per_second: float) -> None:
        if requests_per_second <= 0:
            raise ValueError(
                "requests_per_second must be greater than zero"
            )

        self._interval = 1.0 / requests_per_second
        self._next_request_time = 0.0
        self._backoff_until = 0.0
        self._lock = threading.Lock()

    @property
    def requests_per_second(self) -> float:
        with self._lock:
            return 1.0 / self._interval

    def wait(self) -> None:
        """Wait until this worker is allowed to start another request."""

        with self._lock:
            now = time.monotonic()

            request_time = max(
                now,
                self._next_request_time,
                self._backoff_until,
            )

            wait_time = request_time - now

            self._next_request_time = (
                request_time + self._interval
            )

        if wait_time > 0:
            time.sleep(wait_time)

    def rate_limited(self, retry_after: float) -> float:
        """Globally back off and reduce request rate after HTTP 429."""

        now = time.monotonic()

        with self._lock:
            # Only reduce the rate once for the current rate-limit event.
            # Several workers could see 429 at approximately the same time.
            if now >= self._backoff_until:
                self._interval = min(
                    self._interval * 2.0,
                    2.0,
                )

            self._backoff_until = max(
                self._backoff_until,
                now + retry_after,
            )

            self._next_request_time = max(
                self._next_request_time,
                self._backoff_until,
            )

            return 1.0 / self._interval


# ---------------------------------------------------------------------------
# HTTP status guard
# ---------------------------------------------------------------------------

class HTTPStatusGuard:
    """Detect repeated 403 responses across all worker threads.

    One isolated 403 is treated as a card-specific failure.

    Several consecutive 403 responses are treated as evidence that EDHREC
    may be rejecting the client globally, at which point the import stops.
    """

    def __init__(
        self,
        max_consecutive_403: int = MAX_CONSECUTIVE_403,
    ) -> None:
        self.max_consecutive_403 = max_consecutive_403
        self._consecutive_403 = 0
        self._lock = threading.Lock()

    def record_normal_response(self) -> None:
        """Reset the consecutive 403 counter."""

        with self._lock:
            self._consecutive_403 = 0

    def record_403(self) -> tuple[int, bool]:
        """Record a 403 and return (count, should_stop)."""

        with self._lock:
            self._consecutive_403 += 1

            return (
                self._consecutive_403,
                self._consecutive_403
                >= self.max_consecutive_403,
            )


# ---------------------------------------------------------------------------
# HTTP sessions
# ---------------------------------------------------------------------------

_thread_local = threading.local()


def get_http_session() -> requests.Session:
    """Return one persistent requests.Session per worker thread."""

    session = getattr(
        _thread_local,
        "session",
        None,
    )

    if session is None:
        session = requests.Session()

        session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": (
                    "mtg-database/1.0 "
                    "(EDHREC card metadata importer)"
                ),
            }
        )

        _thread_local.session = session

    return session


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def fetch_edhrec_card(
    oracle_id: str,
    name: str,
    rate_limiter: RequestRateLimiter,
    status_guard: HTTPStatusGuard,
    stop_event: threading.Event,
) -> EDHRECResult:
    """Fetch EDHREC counts for one card."""

    if stop_event.is_set():
        return EDHRECResult(
            oracle_id=oracle_id,
            name=name,
            error="Cancelled",
        )

    slug = get_edhrec_slug(name)

    url = (
        f"https://json.edhrec.com/pages/cards/"
        f"{slug}.json"
    )

    session = get_http_session()

    for attempt in range(1, MAX_RETRIES + 1):
        if stop_event.is_set():
            return EDHRECResult(
                oracle_id=oracle_id,
                name=name,
                error="Cancelled",
            )

        rate_limiter.wait()

        try:
            response = session.get(
                url,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
            )

            # ---------------------------------------------------------------
            # Rate limited
            # ---------------------------------------------------------------

            if response.status_code == 429:
                retry_after_header = response.headers.get(
                    "Retry-After"
                )

                try:
                    retry_after = float(
                        retry_after_header
                    )
                except (TypeError, ValueError):
                    retry_after = (
                        MIN_RATE_LIMIT_BACKOFF
                    )

                retry_after = max(
                    retry_after,
                    MIN_RATE_LIMIT_BACKOFF,
                )

                new_rate = (
                    rate_limiter.rate_limited(
                        retry_after
                    )
                )

                logger.warning(
                    f"EDHREC returned 429 for {name}. "
                    f"Backing off for at least "
                    f"{retry_after:.0f}s. "
                    f"New rate: "
                    f"{new_rate:.2f} requests/sec."
                )

                continue

            # ---------------------------------------------------------------
            # Possible blocking / weird card route
            # ---------------------------------------------------------------

            if response.status_code == 403:
                consecutive_403, should_stop = (
                    status_guard.record_403()
                )

                if should_stop:
                    stop_event.set()

                    return EDHRECResult(
                        oracle_id=oracle_id,
                        name=name,
                        error=(
                            f"EDHREC returned HTTP 403 "
                            f"for {url}. "
                            f"Received "
                            f"{consecutive_403} "
                            f"consecutive 403 responses."
                        ),
                        fatal=True,
                    )

                return EDHRECResult(
                    oracle_id=oracle_id,
                    name=name,
                    error=(
                        f"EDHREC returned HTTP 403 "
                        f"for {url} "
                        f"({consecutive_403} "
                        f"consecutive)"
                    ),
                )

            # Any non-403 response means we are not seeing a continuous
            # stream of access-denied responses.
            status_guard.record_normal_response()

            # ---------------------------------------------------------------
            # Card does not exist on EDHREC
            # ---------------------------------------------------------------

            if response.status_code == 404:
                return EDHRECResult(
                    oracle_id=oracle_id,
                    name=name,
                    error=(
                        f"No EDHREC page found "
                        f"for slug '{slug}'"
                    ),
                )

            # ---------------------------------------------------------------
            # Temporary server problem
            # ---------------------------------------------------------------

            if response.status_code >= 500:
                if attempt < MAX_RETRIES:
                    delay = (
                        2 ** (attempt - 1)
                    ) + random.uniform(
                        0.0,
                        1.0,
                    )

                    logger.warning(
                        f"EDHREC returned HTTP "
                        f"{response.status_code} "
                        f"for {name}. "
                        f"Retrying in "
                        f"{delay:.1f}s."
                    )

                    time.sleep(delay)
                    continue

            response.raise_for_status()

            edhrec_card = (
                response.json()
                ["container"]
                ["json_dict"]
                ["card"]
            )

            return EDHRECResult(
                oracle_id=oracle_id,
                name=name,
                num_decks=int(
                    edhrec_card["num_decks"]
                ),
                potential_decks=int(
                    edhrec_card["potential_decks"]
                ),
            )

        except (
            requests.RequestException,
            KeyError,
            TypeError,
            ValueError,
        ) as error:
            if attempt >= MAX_RETRIES:
                return EDHRECResult(
                    oracle_id=oracle_id,
                    name=name,
                    error=str(error),
                )

            delay = (
                2 ** (attempt - 1)
            ) + random.uniform(
                0.0,
                1.0,
            )

            logger.warning(
                f"Error fetching EDHREC data "
                f"for {name}: {error}. "
                f"Retrying in {delay:.1f}s."
            )

            time.sleep(delay)

    return EDHRECResult(
        oracle_id=oracle_id,
        name=name,
        error="Maximum retries reached",
    )


# ---------------------------------------------------------------------------
# Precompute
# ---------------------------------------------------------------------------

def precompute_card_edhrec(
    db: Session,
    *,
    force: bool = False,
    requests_per_second: float = (
        DEFAULT_REQUESTS_PER_SECOND
    ),
    workers: int = DEFAULT_WORKERS,
    limit: int | None = None,
) -> None:
    """Fetch and persist EDHREC aggregate counts.

    By default only cards missing one or both EDHREC count values are queried.

    With force=True, all cards are queried and existing values are replaced.

    EDHREC groups some multi-faced cards under their primary name, which is
    why the same primary-name slug convention as the other EDHREC precompute
    scripts is used here.
    """

    query = select(
        Card.oracle_id,
        Card.name,
    )

    if not force:
        query = query.where(
            or_(
                Card.num_decks.is_(None),
                Card.potential_decks.is_(None),
            )
        )

    query = query.order_by(Card.name)

    if limit is not None:
        query = query.limit(limit)

    # Only fetch the two fields needed by the HTTP workers.
    # This avoids materializing 30k Card ORM objects into the session.
    cards = db.execute(query).all()

    total = len(cards)

    if total == 0:
        logger.info(
            "No cards require EDHREC deck-count data."
        )
        return

    estimated_seconds = (
        total / requests_per_second
    )

    logger.info(
        f"EDHREC import starting: "
        f"{total:,} cards, "
        f"{workers} workers, "
        f"{requests_per_second:.2f} "
        f"requests/sec max, "
        f"force={force}."
    )

    logger.info(
        f"Theoretical minimum time: "
        f"{estimated_seconds / 60:.1f} "
        f"minutes."
    )

    rate_limiter = RequestRateLimiter(
        requests_per_second
    )

    status_guard = HTTPStatusGuard(
        max_consecutive_403=MAX_CONSECUTIVE_403
    )

    stop_event = threading.Event()

    completed = 0
    succeeded = 0
    failed = 0
    pending_commit = 0

    with ThreadPoolExecutor(
        max_workers=workers
    ) as executor:
        futures = [
            executor.submit(
                fetch_edhrec_card,
                oracle_id,
                name,
                rate_limiter,
                status_guard,
                stop_event,
            )
            for oracle_id, name in cards
        ]

        for future in as_completed(futures):
            # Futures cancelled after a fatal error may raise
            # CancelledError, so skip cancelled futures.
            if future.cancelled():
                continue

            result = future.result()

            completed += 1

            if result.success:
                # Database access stays in the main thread.
                # HTTP workers never touch the SQLAlchemy session.
                db.execute(
                    update(Card)
                    .where(
                        Card.oracle_id
                        == result.oracle_id
                    )
                    .values(
                        num_decks=result.num_decks,
                        potential_decks=(
                            result.potential_decks
                        ),
                    )
                )

                succeeded += 1
                pending_commit += 1

                logger.info(
                    f"[{completed:,}/{total:,}] "
                    f"{result.name}: "
                    f"{result.num_decks:,} decks / "
                    f"{result.potential_decks:,} "
                    f"potential"
                )

                if (
                    pending_commit
                    >= COMMIT_EVERY
                ):
                    db.commit()

                    logger.info(
                        f"Committed progress: "
                        f"{succeeded:,} "
                        f"successful cards."
                    )

                    pending_commit = 0

            else:
                failed += 1

                if result.fatal:
                    logger.error(
                        f"[{completed:,}/{total:,}] "
                        f"{result.name}: "
                        f"{result.error}. "
                        f"Stopping EDHREC import."
                    )

                    stop_event.set()

                    # Cancel tasks that haven't started yet.
                    for pending_future in futures:
                        pending_future.cancel()

                    break

                if result.error != "Cancelled":
                    logger.warning(
                        f"[{completed:,}/{total:,}] "
                        f"{result.name}: "
                        f"{result.error}"
                    )

    # Commit whatever successful results remain.
    if pending_commit > 0:
        db.commit()

        logger.info(
            f"Committed final batch of "
            f"{pending_commit:,} cards."
        )

    logger.info(
        f"EDHREC import finished. "
        f"Successful: {succeeded:,}, "
        f"failed: {failed:,}, "
        f"processed: "
        f"{completed:,}/{total:,}."
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Populate EDHREC card adoption counts."
        )
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Refresh all cards, including cards "
            "that already have EDHREC data."
        ),
    )

    parser.add_argument(
        "--rps",
        type=float,
        default=DEFAULT_REQUESTS_PER_SECOND,
        help=(
            "Maximum EDHREC request starts per second. "
            f"Default: "
            f"{DEFAULT_REQUESTS_PER_SECOND}"
        ),
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=(
            "Number of HTTP worker threads. "
            f"Default: {DEFAULT_WORKERS}"
        ),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Only process this many cards. "
            "Useful for testing."
        ),
    )

    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    args = parse_args()

    create_database()

    db: Session = next(get_db())

    try:
        precompute_card_edhrec(
            db,
            force=args.force,
            requests_per_second=args.rps,
            workers=args.workers,
            limit=args.limit,
        )
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())