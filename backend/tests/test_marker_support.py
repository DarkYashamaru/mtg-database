from __future__ import annotations

import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from database.base import Base
from models import archetype, catalogs, category, color, marker, tag, themes  # noqa: F401
from models.card import Card, Card_Face
from models.marker import CardMarker, Marker
from services.marker_support.engine import refresh_markers


def card(oracle_id: str, name: str, cmc: float, type_line: str, oracle_text: str = "") -> Card:
    result = Card(
        oracle_id=oracle_id, name=name, cmc=cmc, layout="normal",
        commander_legal=True, standard_legal=False,
    )
    result.faces.append(Card_Face(
        parent_id=oracle_id, name=name, cmc=cmc, type_line=type_line, oracle_text=oracle_text,
    ))
    return result


class MarkerProfileEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.db.add_all([
            card("cheap", "Cheap Spell", 2, "Sorcery"),
            card("land", "Cheap Land", 0, "Land"),
            card("self", "Self Trigger", 4, "Creature", "When Self Trigger enters the battlefield, draw a card."),
            card("payoff", "Payoff", 4, "Enchantment", "Whenever another creature enters the battlefield under your control, draw a card."),
            card("instant", "Instant Payoff", 2, "Instant", "Whenever another creature enters the battlefield, draw a card."),
            card("two-basics", "Two Basics", 3, "Sorcery", "Search your library for up to two basic land cards, reveal them, then shuffle."),
            card("two-basics-multiline", "Multiline Two Basics", 3, "Sorcery", "Choose one —\n• Search your library for up to two\n  basic land cards, then shuffle."),
            card("one-basic", "One Basic", 2, "Sorcery", "Search your library for a basic land card, reveal it, then shuffle."),
        ])
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def memberships(self) -> set[tuple[str, str]]:
        return set(self.db.execute(select(CardMarker.marker_id, CardMarker.oracle_id)).all())

    def test_profiles_create_markers_and_match_expected_cards(self) -> None:
        changes = refresh_markers(self.db)
        self.db.commit()

        self.assertGreater(changes, 0)
        self.assertEqual(
            {marker.id for marker in self.db.scalars(select(Marker)).all()},
            {
                "cheap-spell",
                "self-etb",
                "etb-payoff",
                "self-etb-creature",
                "self-etb-artifact",
                "self-etb-enchantment",
                "tutor-two-basic-lands",
            },
        )
        self.assertIn(("cheap-spell", "cheap"), self.memberships())
        self.assertNotIn(("cheap-spell", "land"), self.memberships())
        self.assertIn(("self-etb", "self"), self.memberships())
        self.assertIn(("etb-payoff", "payoff"), self.memberships())
        self.assertNotIn(("etb-payoff", "instant"), self.memberships())
        self.assertIn(("tutor-two-basic-lands", "two-basics"), self.memberships())
        self.assertIn(("tutor-two-basic-lands", "two-basics-multiline"), self.memberships())
        self.assertNotIn(("tutor-two-basic-lands", "one-basic"), self.memberships())

    def test_refresh_is_idempotent_and_removes_stale_membership(self) -> None:
        refresh_markers(self.db)
        self.db.commit()
        self.assertEqual(refresh_markers(self.db), 0)

        payoff = self.db.get(Card_Face, ("payoff", "Payoff"))
        payoff.oracle_text = "Draw a card."
        self.db.commit()
        self.assertEqual(refresh_markers(self.db), 1)
        self.db.commit()
        self.assertNotIn(("etb-payoff", "payoff"), self.memberships())


if __name__ == "__main__":
    unittest.main()
