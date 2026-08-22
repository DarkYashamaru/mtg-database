from __future__ import annotations

import unittest

from backend.scripts.card_metadata_classifier import classify_card_metadata


class CardMetadataClassifierTest(unittest.TestCase):
    def test_marks_card_as_cantrip_when_tag_is_present(self) -> None:
        card = {
            "name": "Spirited Companion",
            "tag_slugs": ["cantrip", "triggered-ability", "hand-neutral"],
            "faces": [],
        }

        metadata = classify_card_metadata(card)
        cantrip = metadata["deckbuilder"]["classifications"]["cantrip"]

        self.assertEqual(["cantrip"], metadata["deckbuilder"]["labels"])
        self.assertTrue(cantrip["matched"])
        self.assertEqual("tag", cantrip["source"])
        self.assertEqual("cantrip", cantrip["tag_slug"])

    def test_does_not_mark_card_without_cantrip_tag(self) -> None:
        card = {
            "name": "Divination",
            "tag_slugs": ["pure-draw", "hand-positive"],
            "faces": [],
        }

        metadata = classify_card_metadata(card)
        cantrip = metadata["deckbuilder"]["classifications"]["cantrip"]

        self.assertEqual([], metadata["deckbuilder"]["labels"])
        self.assertFalse(cantrip["matched"])
        self.assertEqual("tag", cantrip["source"])
        self.assertIsNone(cantrip["tag_slug"])

    def test_handles_missing_tag_list(self) -> None:
        card = {
            "name": "Unknown Card",
            "faces": [],
        }

        metadata = classify_card_metadata(card)
        cantrip = metadata["deckbuilder"]["classifications"]["cantrip"]

        self.assertFalse(cantrip["matched"])
        self.assertEqual([], cantrip["reason_codes"])


if __name__ == "__main__":
    unittest.main()
