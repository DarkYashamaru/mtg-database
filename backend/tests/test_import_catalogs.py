from __future__ import annotations

from contextlib import contextmanager
import unittest
from unittest.mock import Mock, patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from database.base import Base
from models import archetype, catalogs, category, color, marker, tag, themes  # noqa: F401
from models.catalogs import Subtype
from importers import import_catalogs


class SubtypeCatalogImportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    @contextmanager
    def session_scope(self):
        session = Session(self.engine, autoflush=False)
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def response(values: list[str]) -> Mock:
        result = Mock()
        result.json.return_value = {"data": values}
        return result

    def run_import(self, source_values: list[list[str]]) -> None:
        responses = [self.response(values) for values in source_values]
        with (
            patch.object(import_catalogs, "session_scope", self.session_scope),
            patch.object(import_catalogs.requests, "get", side_effect=responses),
        ):
            import_catalogs.download_subtypes()

    def subtype_values(self) -> list[str]:
        return list(self.db.scalars(select(Subtype.value).order_by(Subtype.value)))

    def test_overlapping_catalog_values_are_inserted_once(self) -> None:
        self.run_import([
            ["Clue", "Shrine"],
            ["Siege"],
            ["Shrine", "Wizard"],
            [],
            [],
            [],
            [],
        ])

        self.assertEqual(
            ["Clue", "Plan", "Shrine", "Siege", "Wizard"],
            self.subtype_values(),
        )

    def test_existing_and_manual_subtypes_are_not_reinserted(self) -> None:
        self.db.add_all([Subtype(value="Shrine"), Subtype(value="Plan")])
        self.db.commit()

        self.run_import([
            ["Shrine", "Clue"],
            [],
            [],
            [],
            [],
            [],
            ["Plan"],
        ])

        self.assertEqual(["Clue", "Plan", "Shrine"], self.subtype_values())


if __name__ == "__main__":
    unittest.main()
