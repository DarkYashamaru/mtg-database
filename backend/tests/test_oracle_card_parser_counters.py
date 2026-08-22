from __future__ import annotations

import unittest

from backend.scripts.oracle_card_parser import parse_effects_text, parse_face


class OracleCardParserCountersTest(unittest.TestCase):
    def test_parses_negative_stat_counter(self) -> None:
        effects = parse_effects_text(
            "Put a -1/-1 counter on target creature.",
            "Instill Infection",
        )

        self.assertEqual(
            [
                {
                    "action": "put_counters",
                    "counter_type": "-1/-1",
                    "target": "target_creature",
                    "amount": 1,
                }
            ],
            effects,
        )

    def test_parses_vampiric_tutor_search_clause(self) -> None:
        parsed = parse_face(
            {
                "name": "Vampiric Tutor",
                "type_line": "Instant",
                "oracle_text": "Search your library for a card, then shuffle and put that card on top. You lose 2 life.",
            }
        )

        self.assertEqual(
            [
                {
                    "action": "search_library",
                    "player": "you",
                    "filter": {"card_types": []},
                    "hold_result_as": "that_card",
                },
                {
                    "action": "shuffle_and_move_revealed_card",
                    "object": "that_card",
                    "destination_zone": "top_of_library",
                },
                {
                    "action": "lose_life",
                    "target": "you",
                    "amount": 2,
                },
            ],
            parsed["static_abilities"][0]["effects"],
        )


if __name__ == "__main__":
    unittest.main()
