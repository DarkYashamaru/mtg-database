from __future__ import annotations

import unittest
from types import SimpleNamespace

from pydantic import ValidationError
from app.commander_validation_schemas import COMMANDER_VALIDATION_MAX_SELECTIONS, CommanderValidationRequest
from services.commander_validation import validate_commander_selection


def _entry(value: str):
    return SimpleNamespace(type=SimpleNamespace(value=value))


def _keyword(value: str):
    return SimpleNamespace(keyword=SimpleNamespace(value=value))


def card(
    oracle_id: str,
    name: str,
    *,
    legal: bool = True,
    legendary_creature: bool = True,
    text: str = "",
    keywords: list[str] | None = None,
    subtypes: list[str] | None = None,
):
    return SimpleNamespace(
        oracle_id=oracle_id,
        name=name,
        commander_legal=legal,
        keywords=[_keyword(value) for value in keywords or []],
        faces=[SimpleNamespace(
            oracle_text=text,
            supertypes=[_entry("Legendary")] if legendary_creature else [],
            types=[_entry("Creature")] if legendary_creature else [],
            subtypes=[_entry(value) for value in subtypes or []],
        )],
    )


class CommanderValidationTests(unittest.TestCase):
    def validate(self, *cards):
        return validate_commander_selection(
            {candidate.oracle_id: candidate for candidate in cards},
            [candidate.oracle_id for candidate in cards],
        )

    def test_accepts_legendary_creature_and_explicit_commander_text(self):
        legend = card("legend", "Legend")
        planeswalker = card("walker", "Walker", legendary_creature=False, text="Walker can be your commander.")
        self.assertTrue(self.validate(legend).valid)
        self.assertTrue(self.validate(planeswalker).valid)

    def test_rejects_individually_ineligible_card(self):
        result = self.validate(card("spell", "Spell", legendary_creature=False))
        self.assertFalse(result.valid)
        self.assertEqual(result.code, "not_eligible")

    def test_accepts_partner_and_matching_partner_with(self):
        left = card("left", "Left", keywords=["Partner"])
        right = card("right", "Right", keywords=["Partner"])
        self.assertTrue(self.validate(left, right).valid)

        alpha = card("alpha", "Alpha", text="Partner with Beta (When this creature enters)")
        beta = card("beta", "Beta", text="Partner with Alpha (When this creature enters)")
        self.assertTrue(self.validate(alpha, beta).valid)

    def test_rejects_mismatched_partner_with(self):
        alpha = card("alpha", "Alpha", text="Partner with Beta")
        gamma = card("gamma", "Gamma", text="Partner with Alpha")
        self.assertEqual(self.validate(alpha, gamma).code, "invalid_pair")

    def test_accepts_background_and_doctors_companion_pairs(self):
        leader = card("leader", "Leader", text="Choose a Background")
        background = card("background", "Background", legendary_creature=False, subtypes=["Background"])
        self.assertTrue(self.validate(leader, background).valid)

        companion = card("companion", "Companion", text="Doctor's companion")
        doctor = card("doctor", "Doctor", subtypes=["Time Lord", "Doctor"])
        self.assertTrue(self.validate(companion, doctor).valid)

    def test_rejects_more_than_two_or_duplicate_commanders(self):
        first = card("first", "First")
        second = card("second", "Second")
        third = card("third", "Third")
        self.assertEqual(self.validate(first, second, third).code, "too_many_commanders")
        result = validate_commander_selection({"first": first}, ["first", "first"])
        self.assertEqual(result.code, "duplicate_commander")

    def test_validation_request_supports_full_collection_pools(self):
        selections = [{"oracle_ids": [f"oracle-{index}"]} for index in range(COMMANDER_VALIDATION_MAX_SELECTIONS)]

        request = CommanderValidationRequest(selections=selections)

        self.assertEqual(len(request.selections), COMMANDER_VALIDATION_MAX_SELECTIONS)
        with self.assertRaises(ValidationError):
            CommanderValidationRequest(selections=selections + [{"oracle_ids": ["too-many"]}])


if __name__ == "__main__":
    unittest.main()
