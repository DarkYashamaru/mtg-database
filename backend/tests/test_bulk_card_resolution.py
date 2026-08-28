from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from services.decklist_resolver import resolve_decklist_cards
from models import archetype, catalogs, category, color, marker, tag, themes  # noqa: F401
from models.card import Card


class BulkCardResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        database_path = Path(self.temporary.name) / "test.sqlite"
        self.engine = create_engine(f"sqlite:///{database_path}")
        Card.__table__.create(self.engine)
        self.db = Session(self.engine)
        self.db.add_all([
            Card(oracle_id="exact", name="Reanimate", cmc=1, layout="normal", commander_legal=True, standard_legal=False),
            Card(oracle_id="eirdu", name="Eirdu, Carrier of Dawn // Isilu, Carrier of Twilight", cmc=4, layout="transform", commander_legal=True, standard_legal=False),
            Card(oracle_id="twin-one", name="Twin // One", cmc=1, layout="transform", commander_legal=True, standard_legal=False),
            Card(oracle_id="twin-two", name="Twin // Two", cmc=1, layout="transform", commander_legal=True, standard_legal=False),
        ])
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()
        self.temporary.cleanup()

    def test_resolves_exact_and_unique_front_face_names_and_warns_for_omissions(self) -> None:
        cards, warnings = resolve_decklist_cards(
            ["Reanimate", "Eirdu, Carrier of Dawn", "Missing Card", "Twin"], self.db
        )

        self.assertEqual(
            [(requested, card.name) for requested, card in cards],
            [
                ("Reanimate", "Reanimate"),
                ("Eirdu, Carrier of Dawn", "Eirdu, Carrier of Dawn // Isilu, Carrier of Twilight"),
            ],
        )
        self.assertEqual(
            warnings,
            [
                'Resolved "Eirdu, Carrier of Dawn" as "Eirdu, Carrier of Dawn // Isilu, Carrier of Twilight".',
                'Skipped "Missing Card": no card found.',
                'Skipped "Twin": multiple cards matched (Twin // One; Twin // Two).',
            ],
        )


if __name__ == "__main__":
    unittest.main()
