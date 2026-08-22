from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.scripts import oracle_card_parser


class OracleCardParserSqliteExportTest(unittest.TestCase):
    def test_exports_cards_to_sqlite_with_json_payload(self) -> None:
        cards = [
            {
                "oracle_id": "card-1",
                "name": "Cremate",
                "cmc": 1.0,
                "layout": "normal",
                "tag_slugs": ["cantrip"],
                "faces": [
                    {
                        "name": "Cremate",
                        "cmc": 1.0,
                        "type_line": "Instant",
                        "oracle_text": "Exile target card from a graveyard.\nDraw a card.",
                    }
                ],
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            database_path = Path(tmpdir) / "card_classification.sqlite"
            with patch.object(oracle_card_parser, "load_cards", return_value=cards):
                count = oracle_card_parser.export_cards_to_sqlite(database_path=database_path)

            self.assertEqual(1, count)

            conn = sqlite3.connect(database_path)
            try:
                row = conn.execute(
                    """
                    select export_scope, oracle_id, name, payload_json, schema_version
                    from card_classifications
                    """
                ).fetchone()
            finally:
                conn.close()

            self.assertIsNotNone(row)
            self.assertEqual("cards", row[0])
            self.assertEqual("card-1", row[1])
            self.assertEqual("Cremate", row[2])
            self.assertEqual(1, row[4])

            payload = json.loads(row[3])
            self.assertEqual("Cremate", payload["name"])
            self.assertEqual(["cantrip"], payload["metadata"]["deckbuilder"]["labels"])

    def test_keeps_card_and_commander_exports_in_same_database(self) -> None:
        cards = [
            {
                "oracle_id": "shared-card",
                "name": "Commander Card",
                "cmc": 2.0,
                "layout": "normal",
                "tag_slugs": [],
                "faces": [
                    {
                        "name": "Commander Card",
                        "cmc": 2.0,
                        "type_line": "Legendary Creature — Wizard",
                        "oracle_text": "Draw a card.",
                    }
                ],
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            database_path = Path(tmpdir) / "card_classification.sqlite"
            with patch.object(oracle_card_parser, "load_cards", return_value=cards):
                oracle_card_parser.export_cards_to_sqlite(
                    database_path=database_path,
                    commander_only=False,
                )
                oracle_card_parser.export_cards_to_sqlite(
                    database_path=database_path,
                    commander_only=True,
                )

            conn = sqlite3.connect(database_path)
            try:
                rows = conn.execute(
                    """
                    select export_scope, oracle_id
                    from card_classifications
                    order by export_scope
                    """
                ).fetchall()
            finally:
                conn.close()

            self.assertEqual(
                [("cards", "shared-card"), ("commanders", "shared-card")],
                rows,
            )


if __name__ == "__main__":
    unittest.main()
