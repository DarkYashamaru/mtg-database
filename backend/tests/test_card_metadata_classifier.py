from __future__ import annotations

import unittest

from backend.scripts.card_metadata_classifier import classify_card_metadata


class CardMetadataClassifierTest(unittest.TestCase):
    def test_marks_card_as_cantrip_when_tag_is_present(self) -> None:
        card = {
            "name": "Spirited Companion",
            "tag_ids": ["42313c19-8be2-47d9-9d3a-99c39725b87d", "other-tag"],
            "faces": [],
        }

        metadata = classify_card_metadata(card)
        cantrip = metadata["deckbuilder"]["classifications"]["cantrip"]

        self.assertEqual(["cantrip"], metadata["deckbuilder"]["labels"])
        self.assertTrue(cantrip["matched"])
        self.assertEqual("tag", cantrip["source"])
        self.assertEqual("42313c19-8be2-47d9-9d3a-99c39725b87d", cantrip["tag_id"])

    def test_does_not_mark_card_without_cantrip_tag(self) -> None:
        card = {
            "name": "Divination",
            "tag_ids": ["other-tag"],
            "faces": [],
        }

        metadata = classify_card_metadata(card)
        cantrip = metadata["deckbuilder"]["classifications"]["cantrip"]

        self.assertEqual([], metadata["deckbuilder"]["labels"])
        self.assertFalse(cantrip["matched"])
        self.assertEqual("tag", cantrip["source"])
        self.assertIsNone(cantrip["tag_id"])

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
