from __future__ import annotations

import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from models import archetype, catalogs, category, color, marker, tag, themes  # noqa: F401
from models.card import Card, Card_Face
from models.tag import Tag, Tagging
from services.search_filters import (
    TagSearchTerm,
    card_cmc_match_clauses,
    card_tag_match_clause,
    card_type_match_clause,
    parse_tag_search_terms,
    resolve_tag_ids,
)


class AdvancedCardTypeSearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Card.__table__.create(self.engine)
        Card_Face.__table__.create(self.engine)
        Tag.__table__.create(self.engine)
        Tagging.__table__.create(self.engine)
        self.db = Session(self.engine)

        self.add_card(
            "legendary-soldier",
            ["Legendary Creature — Human Soldier"],
        )
        self.add_card(
            "legendary-wizard",
            ["Legendary Creature — Human Wizard"],
        )
        self.add_card(
            "legendary-artifact-soldier",
            ["Legendary Artifact Creature — Soldier"],
        )
        self.add_card(
            "ordinary-soldier",
            ["Creature — Human Soldier"],
        )
        self.add_card(
            "terms-on-different-faces",
            ["Legendary Creature — Human Wizard", "Creature — Soldier"],
        )
        self.add_tag("tag-bounceland", "bounceland", "Bounceland")
        self.add_tag(
            "tag-rav-bounceland",
            "cycle-rav-bounceland",
            "Ravnica Bounceland",
        )
        self.add_tag("tag-label-match", "guild-bounce", "Guild Bounceland")
        self.add_tag("tag-landfall", "landfall", "Landfall")
        self.add_tagged_card("tag-exact-card", ["tag-bounceland"])
        self.add_tagged_card("tag-rav-card", ["tag-rav-bounceland"])
        self.add_tagged_card(
            "tag-rav-landfall-card",
            ["tag-rav-bounceland", "tag-landfall"],
        )
        self.add_tagged_card("tag-label-card", ["tag-label-match"])
        self.add_tagged_card("tag-plain-card", [])
        self.db.commit()
        self.add_cmc_card("cmc-zero-card", 0)
        self.add_cmc_card("cmc-three-card", 3)
        self.add_cmc_card("cmc-four-card", 4)
        self.add_cmc_card("cmc-six-card", 6)

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def add_card(self, oracle_id: str, type_lines: list[str]) -> None:
        self.db.add(Card(
            oracle_id=oracle_id,
            name=oracle_id,
            cmc=3,
            layout="transform" if len(type_lines) > 1 else "normal",
            commander_legal=True,
            standard_legal=False,
        ))
        for index, type_line in enumerate(type_lines):
            self.db.add(Card_Face(
                parent_id=oracle_id,
                name=f"{oracle_id}-{index}",
                mana_cost="{3}",
                cmc=3,
                oracle_text="",
                power="3",
                toughness="3",
                type_line=type_line,
                small_image=None,
                normal_image=None,
                large_image=None,
            ))

    def add_tag(self, tag_id: str, slug: str, label: str) -> None:
        self.db.add(Tag(id=tag_id, slug=slug, label=label, description=None))


    def add_cmc_card(self, oracle_id: str, cmc: float) -> None:
        self.db.add(Card(
            oracle_id=oracle_id,
            name=oracle_id,
            cmc=cmc,
            layout="normal",
            commander_legal=True,
            standard_legal=False,
        ))
    def add_tagged_card(self, oracle_id: str, tag_ids: list[str]) -> None:
        self.db.add(Card(
            oracle_id=oracle_id,
            name=oracle_id,
            cmc=0,
            layout="normal",
            commander_legal=True,
            standard_legal=False,
        ))
        for tag_id in tag_ids:
            self.db.add(Tagging(
                tag_id=tag_id,
                oracle_id=oracle_id,
                annotation=None,
            ))

    def matching_tag_ids(
        self,
        include: list[str] | None = None,
        exclude: list[str] | None = None,
    ) -> set[str]:
        statement = select(Card.oracle_id).where(Card.oracle_id.like("tag-%-card"))
        for term in parse_tag_search_terms(include or []):
            statement = statement.where(
                card_tag_match_clause(resolve_tag_ids(self.db, term))
            )
        for term in parse_tag_search_terms(exclude or []):
            statement = statement.where(
                ~card_tag_match_clause(resolve_tag_ids(self.db, term))
            )
        return set(self.db.scalars(statement))

    def matching_ids(self, card_type: str) -> set[str]:
        clause = card_type_match_clause(card_type)
        statement = select(Card.oracle_id)
        if clause is not None:
            statement = statement.where(clause)
        return set(self.db.scalars(statement))

    def matching_cmc_ids(
        self,
        cmc_min: float | None = None,
        cmc_max: float | None = None,
    ) -> set[str]:
        statement = select(Card.oracle_id).where(Card.oracle_id.like("cmc-%-card"))
        statement = statement.where(*card_cmc_match_clauses(cmc_min, cmc_max))
        return set(self.db.scalars(statement))

    def test_legacy_contiguous_phrase_still_matches(self) -> None:
        self.assertEqual(
            self.matching_ids("Legendary Creature"),
            {
                "legendary-soldier",
                "legendary-wizard",
                "terms-on-different-faces",
            },
        )

    def test_cmc_minimum_is_inclusive(self) -> None:
        self.assertEqual(
            self.matching_cmc_ids(cmc_min=4),
            {"cmc-four-card", "cmc-six-card"},
        )

    def test_cmc_maximum_is_inclusive_and_accepts_zero(self) -> None:
        self.assertEqual(
            self.matching_cmc_ids(cmc_max=3),
            {"cmc-zero-card", "cmc-three-card"},
        )

    def test_cmc_range_applies_both_bounds(self) -> None:
        self.assertEqual(
            self.matching_cmc_ids(cmc_min=3, cmc_max=4),
            {"cmc-three-card", "cmc-four-card"},
        )

    def test_cmc_bounds_reject_invalid_ranges(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-negative"):
            card_cmc_match_clauses(-1, None)
        with self.assertRaisesRegex(ValueError, "cannot be greater"):
            card_cmc_match_clauses(5, 4)

    def test_comma_separated_terms_are_case_insensitive_and_require_every_term(self) -> None:
        self.assertEqual(
            self.matching_ids("legendary, CREATURE, Soldier"),
            {"legendary-soldier", "legendary-artifact-soldier"},
        )

    def test_all_terms_must_match_the_same_face(self) -> None:
        self.assertNotIn(
            "terms-on-different-faces",
            self.matching_ids("Legendary, Creature, Soldier"),
        )

    def test_quoted_phrases_remain_intact(self) -> None:
        self.assertEqual(
            self.matching_ids('"Legendary Creature", Soldier'),
            {"legendary-soldier"},
        )

    def test_unquoted_tag_term_matches_slug_and_label_substrings(self) -> None:
        self.assertEqual(
            self.matching_tag_ids(include=["bounceland"]),
            {
                "tag-exact-card",
                "tag-rav-card",
                "tag-rav-landfall-card",
                "tag-label-card",
            },
        )

    def test_tag_suffix_fragment_matches_only_tags_containing_fragment(self) -> None:
        self.assertEqual(
            self.matching_tag_ids(include=["-bounceland"]),
            {"tag-rav-card", "tag-rav-landfall-card"},
        )

    def test_quoted_tag_term_is_an_exact_case_insensitive_match(self) -> None:
        self.assertEqual(
            self.matching_tag_ids(include=['"BOUNCELAND"']),
            {"tag-exact-card"},
        )
        self.assertEqual(
            self.matching_tag_ids(include=['"guild bounceland"']),
            {"tag-label-card"},
        )

    def test_multiple_tag_terms_keep_and_semantics(self) -> None:
        self.assertEqual(
            self.matching_tag_ids(include=["bounceland, landfall"]),
            {"tag-rav-landfall-card"},
        )

    def test_tag_exclusions_support_partial_and_exact_matching(self) -> None:
        self.assertEqual(
            self.matching_tag_ids(exclude=["bounceland"]),
            {"tag-plain-card"},
        )
        self.assertEqual(
            self.matching_tag_ids(exclude=['"bounceland"']),
            {
                "tag-rav-card",
                "tag-rav-landfall-card",
                "tag-label-card",
                "tag-plain-card",
            },
        )

    def test_tag_parser_handles_repeated_params_and_malformed_quotes_safely(self) -> None:
        self.assertEqual(
            parse_tag_search_terms([
                'bounceland, "draw-engine"',
                "-bounceland",
                '"unfinished',
            ]),
            [
                TagSearchTerm("bounceland", exact=False),
                TagSearchTerm("draw-engine", exact=True),
                TagSearchTerm("-bounceland", exact=False),
                TagSearchTerm('"unfinished', exact=False),
            ],
        )

    def test_sql_wildcards_in_tag_terms_are_literal(self) -> None:
        self.assertEqual(self.matching_tag_ids(include=["%"]), set())
        self.assertEqual(self.matching_tag_ids(include=["_"]), set())


if __name__ == "__main__":
    unittest.main()
