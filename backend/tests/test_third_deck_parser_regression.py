from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path

from backend.scripts import oracle_card_parser


ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = ROOT / "backend" / "cards.sqlite"
DECKLIST_PATH = Path(__file__).with_name("test_third_decklist.txt")


def load_deck_card_names() -> list[str]:
    names: list[str] = []
    for line in DECKLIST_PATH.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        _, name = line.split(" ", 1)
        names.append(name)
    return sorted(set(names))


def collect_custom_nodes(obj: object) -> list[str]:
    custom: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            if node.get("action") == "custom_effect":
                custom.append(f"effect: {node.get('text')}")
            if node.get("type") == "custom":
                custom.append(f"trigger: {node.get('text')}")
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(obj)
    return custom


class ThirdDeckParserRegressionTest(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.conn = sqlite3.connect(DATABASE_PATH)
        cls.conn.row_factory = sqlite3.Row
        cls.card_names = load_deck_card_names()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.conn.close()

    def fetch_faces(self, card_name: str) -> list[dict[str, str]]:
        cur = self.conn.cursor()
        cur.execute(
            """
            select f.name, f.type_line, f.oracle_text
            from cards c
            join card_faces f on f.parent_id = c.oracle_id
            where c.name = ?
            order by f.name
            """,
            (card_name,),
        )
        rows = cur.fetchall()
        return [
            {
                "name": row["name"],
                "type_line": row["type_line"],
                "oracle_text": row["oracle_text"],
            }
            for row in rows
        ]

    def test_third_deck_cards_have_no_custom_nodes(self) -> None:
        missing: list[str] = []
        failures: list[str] = []

        for card_name in self.card_names:
            faces = self.fetch_faces(card_name)
            if not faces:
                missing.append(card_name)
                continue

            parsed_faces = [oracle_card_parser.parse_face(face) for face in faces]
            custom_nodes = collect_custom_nodes(parsed_faces)
            if custom_nodes:
                failures.append(f"{card_name}: " + "; ".join(custom_nodes))

        self.assertEqual([], missing, f"Cards missing from database: {missing}")
        self.assertEqual([], failures, "Cards with custom parser nodes:\n" + "\n".join(failures))


if __name__ == "__main__":
    unittest.main()
