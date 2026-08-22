from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import select

from backend.database.classification_session import classification_session_scope
from backend.database.create_classification_database import create_classification_database
from backend.models.card_classification import ParsedAbility, ParsedEffect, ParsedFace
from backend.scripts import oracle_card_parser
from backend.scripts.flatten_card_classifications import flatten_card_classifications


class FlattenCardClassificationsTest(unittest.TestCase):
    def test_flattens_faces_abilities_and_effects(self) -> None:
        cards = [
            {
                "oracle_id": "card-1",
                "name": "Vampiric Tutor",
                "cmc": 1.0,
                "layout": "normal",
                "tag_slugs": [],
                "faces": [
                    {
                        "name": "Vampiric Tutor",
                        "cmc": 1.0,
                        "type_line": "Instant",
                        "oracle_text": "Search your library for a card, then shuffle and put that card on top. You lose 2 life.",
                    }
                ],
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            database_path = Path(tmpdir) / "card_classification.sqlite"
            with patch.object(oracle_card_parser, "load_cards", return_value=cards):
                oracle_card_parser.export_cards_to_sqlite(database_path=database_path)

            create_classification_database(database_path)
            with classification_session_scope(database_path) as db:
                counts = flatten_card_classifications(db, export_scope="cards")

            self.assertEqual((1, 1, 1, 3), counts)

            with classification_session_scope(database_path) as db:
                faces = list(db.execute(select(ParsedFace)).scalars())
                abilities = list(db.execute(select(ParsedAbility)).scalars())
                effects = list(db.execute(select(ParsedEffect).order_by(ParsedEffect.effect_index)).scalars())

            self.assertEqual(1, len(faces))
            self.assertEqual(1, len(abilities))
            self.assertEqual(
                ["search_library", "shuffle_and_move_revealed_card", "lose_life"],
                [effect.action for effect in effects],
            )
            self.assertIsNone(effects[0].target_signature)


if __name__ == "__main__":
    unittest.main()
