from __future__ import annotations

import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from database.base import Base
from database.create_database import create_database
from importers import import_oracle_cards as oracle_importer
from importers.import_oracle_cards import get_card_faces
from models.card import Card, Card_Face
from models.printing import CardPrinting, PrintingValue


class CardFaceSchemaTests(unittest.TestCase):
    def test_continuation_face_without_type_line_is_preserved(self) -> None:
        faces = get_card_faces(
            {
                "oracle_id": "roll-for-initiative",
                "layout": "split",
                "card_faces": [
                    {
                        "name": "Roll for Initiative",
                        "type_line": "Sorcery",
                        "cmc": 0,
                    },
                    {
                        "name": "Roll for Initiative (cont'd)",
                        "cmc": 0,
                    },
                ],
            }
        )

        self.assertEqual(2, len(faces))
        self.assertEqual(1, faces[1].face_index)
        self.assertIsNone(faces[1].type_line)

    def test_database_upgrade_relaxes_face_type_line_constraint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "cards.sqlite"
            upgrade_engine = create_engine(f"sqlite:///{database_path}")
            Card.__table__.create(upgrade_engine)

            with upgrade_engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        CREATE TABLE card_faces (
                            parent_id VARCHAR(36) NOT NULL,
                            face_index INTEGER NOT NULL,
                            name VARCHAR(255) NOT NULL,
                            mana_cost VARCHAR(100),
                            cmc FLOAT NOT NULL,
                            oracle_text TEXT,
                            power VARCHAR(20),
                            toughness VARCHAR(20),
                            type_line VARCHAR(255) NOT NULL,
                            small_image VARCHAR(255),
                            normal_image VARCHAR(255),
                            large_image VARCHAR(255),
                            PRIMARY KEY (parent_id, face_index),
                            FOREIGN KEY(parent_id) REFERENCES cards (oracle_id)
                        )
                        """
                    )
                )

            with patch("database.create_database.engine", upgrade_engine):
                create_database()

            columns = {
                column["name"]: column
                for column in inspect(upgrade_engine).get_columns("card_faces")
            }
            self.assertTrue(columns["type_line"]["nullable"])
            upgrade_engine.dispose()

    def test_split_and_flip_faces_inherit_parent_images(self) -> None:
        parent_images = {
            "small": "https://example.test/small.jpg",
            "normal": "https://example.test/normal.jpg",
            "large": "https://example.test/large.jpg",
        }

        for layout in ("split", "flip"):
            with self.subTest(layout=layout):
                faces = get_card_faces(
                    {
                        "oracle_id": f"{layout}-card",
                        "layout": layout,
                        "image_uris": parent_images,
                        "card_faces": [
                            {"name": "Front", "cmc": 1, "type_line": "Instant"},
                            {"name": "Back", "cmc": 1, "type_line": "Instant"},
                        ],
                    }
                )
                self.assertEqual(parent_images["small"], faces[0].small_image)
                self.assertEqual(parent_images["normal"], faces[1].normal_image)
                self.assertEqual(parent_images["large"], faces[1].large_image)

    def test_transform_faces_keep_their_own_images(self) -> None:
        faces = get_card_faces(
            {
                "oracle_id": "transform-card",
                "layout": "transform",
                "image_uris": {"small": "https://example.test/parent-front.jpg"},
                "card_faces": [
                    {
                        "name": "Day",
                        "cmc": 1,
                        "type_line": "Creature",
                        "image_uris": {"small": "https://example.test/day.jpg"},
                    },
                    {
                        "name": "Night",
                        "cmc": 1,
                        "type_line": "Creature",
                        "image_uris": {"small": "https://example.test/night.jpg"},
                    },
                ],
            }
        )

        self.assertEqual("https://example.test/day.jpg", faces[0].small_image)
        self.assertEqual("https://example.test/night.jpg", faces[1].small_image)

    def test_backfill_updates_non_commander_shared_front_card(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "oracle-cards.json"
            source_path.touch()
            temporary_engine = create_engine("sqlite:///:memory:")
            Base.metadata.create_all(temporary_engine)

            with Session(temporary_engine) as session:
                session.add(Card(
                    oracle_id="split-card",
                    name="Split Card",
                    cmc=2,
                    layout="split",
                    commander_legal=False,
                    standard_legal=False,
                ))
                session.add(Card_Face(
                    parent_id="split-card",
                    face_index=0,
                    name="First Half",
                    cmc=1,
                    type_line="Instant",
                ))
                session.commit()

            @contextmanager
            def temporary_session_scope():
                session = Session(temporary_engine)
                try:
                    yield session
                except Exception:
                    session.rollback()
                    raise
                finally:
                    session.close()

            payload = [{
                "oracle_id": "split-card",
                "layout": "split",
                "legalities": {"commander": "not_legal"},
                "image_uris": {"small": "https://example.test/split.jpg"},
            }]
            with (
                patch.object(oracle_importer, "session_scope", temporary_session_scope),
                patch.object(oracle_importer, "load_scryfall_bulk_items", return_value=payload),
            ):
                self.assertEqual(1, oracle_importer.backfill_shared_front_face_images(source_path))

            with Session(temporary_engine) as session:
                face = session.get(Card_Face, ("split-card", 0))
                self.assertEqual("https://example.test/split.jpg", face.small_image)
            temporary_engine.dispose()

    def test_database_upgrade_preserves_printing_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "cards.sqlite"
            upgrade_engine = create_engine(f"sqlite:///{database_path}")
            Card.__table__.create(upgrade_engine)
            CardPrinting.__table__.create(upgrade_engine)

            with upgrade_engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        CREATE TABLE printing_values (
                            printing_id VARCHAR(36) NOT NULL,
                            field VARCHAR(64) NOT NULL,
                            value VARCHAR(255) NOT NULL,
                            position INTEGER NOT NULL,
                            PRIMARY KEY (printing_id, field, value),
                            FOREIGN KEY(printing_id) REFERENCES card_printings (id)
                        )
                        """
                    )
                )
                connection.execute(
                    text(
                        """
                        INSERT INTO printing_values (printing_id, field, value, position)
                        VALUES ('printing', 'multiverse_ids', '123', 0)
                        """
                    )
                )

            with patch("database.create_database.engine", upgrade_engine):
                create_database()

            self.assertEqual(
                ["printing_id", "field", "position"],
                inspect(upgrade_engine)
                .get_pk_constraint("printing_values")
                .get("constrained_columns"),
            )
            with upgrade_engine.connect() as connection:
                value = connection.execute(
                    text("SELECT value FROM printing_values WHERE position = 0")
                ).scalar_one()
            self.assertEqual("123", value)
            upgrade_engine.dispose()

    def test_printing_value_retains_duplicate_array_members(self) -> None:
        temporary_engine = create_engine("sqlite:///:memory:")
        CardPrinting.__table__.create(temporary_engine)
        PrintingValue.__table__.create(temporary_engine)
        with Session(temporary_engine) as session:
            session.add(CardPrinting(
                id="printing",
                lang="en",
                object="card",
                layout="normal",
                name="Example",
                cmc=0,
                border_color="black",
                collector_number="1",
                digital=False,
                frame="2015",
                full_art=False,
                highres_image=False,
                image_status="missing",
                oversized=False,
                promo=False,
                rarity="common",
                reprint=False,
                set_code="tst",
                set_id="set",
                set_name="Test Set",
                set_type="test",
                story_spotlight=False,
                textless=False,
                variation=False,
            ))
            session.add_all([
                PrintingValue(
                    printing_id="printing",
                    field="multiverse_ids",
                    position=0,
                    value="534625",
                ),
                PrintingValue(
                    printing_id="printing",
                    field="multiverse_ids",
                    position=1,
                    value="534625",
                ),
            ])
            session.commit()
            self.assertEqual(
                2,
                session.query(PrintingValue)
                .filter_by(printing_id="printing", field="multiverse_ids")
                .count(),
            )
        temporary_engine.dispose()


if __name__ == "__main__":
    unittest.main()
