from __future__ import annotations

from contextlib import contextmanager
from unittest import TestCase
from unittest.mock import patch

import requests
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from database.base import Base
from models.card import Card, CardRuling
from importers import import_rulings


class RulingsImportTests(TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            session.add(
                Card(
                    oracle_id="card-1",
                    name="Test Card",
                    cmc=1,
                    layout="normal",
                    rulings_uri="https://example.test/rulings",
                    commander_legal=False,
                    standard_legal=False,
                )
            )
            session.commit()

    def tearDown(self) -> None:
        self.engine.dispose()

    @contextmanager
    def session_scope(self):
        session = Session(self.engine)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def card(self) -> Card:
        with Session(self.engine) as session:
            return session.scalar(select(Card).where(Card.oracle_id == "card-1"))

    def test_successful_response_is_saved_once_and_then_skipped(self) -> None:
        payload = [
            {
                "source": "wotc",
                "published_at": "2020-01-01",
                "comment": "A ruling.",
            }
        ]
        with (
            patch.object(import_rulings, "session_scope", self.session_scope),
            patch.object(
                import_rulings, "_fetch_rulings", return_value=payload
            ) as fetch,
        ):
            self.assertEqual(import_rulings.import_card_rulings(), 1)
            self.assertEqual(import_rulings.import_card_rulings(), 0)

        self.assertEqual(fetch.call_count, 1)
        self.assertIsNotNone(self.card().rulings_fetched_at)
        with Session(self.engine) as session:
            rulings = session.scalars(select(CardRuling)).all()
        self.assertEqual([(ruling.position, ruling.comment) for ruling in rulings], [(0, "A ruling.")])

    def test_empty_response_is_marked_as_checked(self) -> None:
        with (
            patch.object(import_rulings, "session_scope", self.session_scope),
            patch.object(import_rulings, "_fetch_rulings", return_value=[]) as fetch,
        ):
            self.assertEqual(import_rulings.import_card_rulings(), 0)
            self.assertEqual(import_rulings.import_card_rulings(), 0)

        self.assertEqual(fetch.call_count, 1)
        self.assertIsNotNone(self.card().rulings_fetched_at)

    def test_failed_response_remains_eligible_for_retry(self) -> None:
        with (
            patch.object(import_rulings, "session_scope", self.session_scope),
            patch.object(
                import_rulings,
                "_fetch_rulings",
                side_effect=[requests.RequestException("temporary"), []],
            ) as fetch,
        ):
            self.assertEqual(import_rulings.import_card_rulings(), 0)
            self.assertIsNone(self.card().rulings_fetched_at)
            self.assertEqual(import_rulings.import_card_rulings(), 0)

        self.assertEqual(fetch.call_count, 2)
        self.assertIsNotNone(self.card().rulings_fetched_at)


if __name__ == "__main__":
    import unittest

    unittest.main()
