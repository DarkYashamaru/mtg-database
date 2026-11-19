from __future__ import annotations

from datetime import date, datetime, timezone
from time import monotonic, sleep

import requests
from sqlalchemy import select

from database.session import session_scope
from downloaders.scryfall_download_utility import REQUEST_HEADERS
from models.card import Card, CardRuling
from tools.logger import logger

REQUEST_DELAY_SECONDS = 0.1
COMMIT_BATCH_SIZE = 100


def _fetch_rulings(session: requests.Session, uri: str) -> list[dict[str, object]]:
    rulings: list[dict[str, object]] = []
    next_uri: str | None = uri
    while next_uri:
        response = session.get(next_uri, headers=REQUEST_HEADERS, timeout=30)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise ValueError(f"Invalid rulings response from {next_uri}.")
        rulings.extend(item for item in payload["data"] if isinstance(item, dict))
        candidate = payload.get("next_page") if payload.get("has_more") else None
        next_uri = candidate if isinstance(candidate, str) else None
    return rulings


def import_card_rulings() -> int:
    """Fetch rulings only for Oracle cards not successfully checked before."""
    imported = 0
    failures = 0
    last_request_at: float | None = None

    with session_scope() as database_session, requests.Session() as http_session:
        cards = list(
            database_session.scalars(
                select(Card)
                .where(
                    Card.rulings_uri.is_not(None),
                    Card.rulings_fetched_at.is_(None),
                )
                .order_by(Card.oracle_id)
            )
        )
        total = len(cards)
        for index, card in enumerate(cards, start=1):
            if last_request_at is not None:
                remaining = REQUEST_DELAY_SECONDS - (monotonic() - last_request_at)
                if remaining > 0:
                    sleep(remaining)
            last_request_at = monotonic()

            try:
                payload = _fetch_rulings(http_session, card.rulings_uri)
                rows = [
                    CardRuling(
                        oracle_id=card.oracle_id,
                        position=position,
                        source=str(ruling["source"]),
                        published_at=date.fromisoformat(str(ruling["published_at"])),
                        comment=str(ruling["comment"]),
                    )
                    for position, ruling in enumerate(payload)
                ]
            except (KeyError, TypeError, ValueError, requests.RequestException) as error:
                failures += 1
                logger.warning("Could not import rulings for %s: %s", card.oracle_id, error)
                continue

            database_session.add_all(rows)
            # Empty responses are successful too: remember them so cards
            # without rulings are not requested on every refresh.
            card.rulings_fetched_at = datetime.now(timezone.utc)
            imported += len(rows)
            if index % COMMIT_BATCH_SIZE == 0:
                database_session.commit()
                logger.info("Checked rulings for %s/%s cards", index, total)

    logger.info(
        "Checked rulings for %s cards; imported %s rulings; %s card requests failed",
        total - failures,
        imported,
        failures,
    )
    return imported
