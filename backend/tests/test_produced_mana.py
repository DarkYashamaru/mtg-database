from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import types
import unittest
from unittest.mock import Mock, patch

from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session, selectinload

from database.base import Base
from models import archetype, catalogs, category, marker, tag, themes  # noqa: F401
from models.card import Card
from models.catalogs import CardType
from models.color import CardProducedMana, Color
from models.public_schemas import card_to_schema

logger_module = types.ModuleType("tools.logger")
logger_module.logger = Mock()
with patch.dict(sys.modules, {"tools.logger": logger_module}):
    from importers import import_oracle_cards as oracle_importer


class ProducedManaImportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.temporary_directory = TemporaryDirectory()
        self.source_path = Path(self.temporary_directory.name) / "oracle-cards.json"
        self.source_path.touch()

        for color_id, (name, symbol) in enumerate(
            (
                ("White", "W"),
                ("Blue", "U"),
                ("Black", "B"),
                ("Red", "R"),
                ("Green", "G"),
                ("Colorless", "C"),
            ),
            start=1,
        ):
            self.db.add(Color(id=color_id, name=name, symbol=symbol))
        self.db.add(CardType(value="Land"))
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()
        self.temporary_directory.cleanup()

    @contextmanager
    def session_scope(self):
        session = Session(self.engine)
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def add_existing_card(self, oracle_id: str = "existing-card") -> Card:
        card = Card(
            oracle_id=oracle_id,
            name="Existing Land",
            cmc=0,
            layout="normal",
            commander_legal=True,
            standard_legal=False,
        )
        self.db.add(card)
        self.db.commit()
        return card

    @staticmethod
    def scryfall_card(
        oracle_id: str,
        produced_mana: list[str] | None,
    ) -> dict[str, object]:
        return {
            "oracle_id": oracle_id,
            "name": f"Land {oracle_id}",
            "cmc": 0,
            "layout": "normal",
            "legalities": {"commander": "legal", "standard": "not_legal"},
            "keywords": [],
            "color_identity": [],
            "produced_mana": produced_mana,
            "type_line": "Land",
            "mana_cost": "",
            "oracle_text": "",
            "power": None,
            "toughness": None,
            "image_uris": {},
        }

    def run_import(self, payload: list[dict[str, object]]) -> int:
        with (
            patch.object(oracle_importer, "session_scope", self.session_scope),
            patch.object(
                oracle_importer,
                "load_scryfall_bulk_items",
                return_value=payload,
            ),
        ):
            return oracle_importer.import_oracle_cards(self.source_path)

    def schema_for(self, oracle_id: str):
        self.db.expire_all()
        card = self.db.scalar(
            select(Card)
            .where(Card.oracle_id == oracle_id)
            .options(
                selectinload(Card.produced_mana).selectinload(CardProducedMana.color)
            )
        )
        self.assertIsNotNone(card)
        return card_to_schema(card, {}, {})

    def test_import_backfills_existing_cards_and_imports_new_cards(self) -> None:
        self.add_existing_card()
        payload = [
            self.scryfall_card(
                "existing-card",
                ["C", "W", "R", "W", "X"],
            ),
            self.scryfall_card("new-card", ["G", "U"]),
        ]

        imported_count = self.run_import(payload)

        self.assertEqual(imported_count, 1)
        self.assertEqual(
            [color.symbol for color in self.schema_for("existing-card").produced_mana],
            ["W", "R", "C"],
        )
        self.assertEqual(
            [color.symbol for color in self.schema_for("new-card").produced_mana],
            ["U", "G"],
        )
        self.assertIn("card_produced_mana", inspect(self.engine).get_table_names())

    def test_refresh_removes_stale_capabilities_and_serializes_empty_values(self) -> None:
        card = self.add_existing_card()
        white = self.db.scalar(select(Color).where(Color.symbol == "W"))
        self.db.add(CardProducedMana(card_id=card.oracle_id, color_id=white.id))
        self.db.commit()

        imported_count = self.run_import(
            [self.scryfall_card("existing-card", None)]
        )

        self.assertEqual(imported_count, 0)
        self.assertEqual(self.db.scalars(select(CardProducedMana)).all(), [])
        self.assertEqual(self.schema_for("existing-card").produced_mana, [])


if __name__ == "__main__":
    unittest.main()
