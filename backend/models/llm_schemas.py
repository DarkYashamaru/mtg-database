
from pydantic import BaseModel

class ArchetypeReasoningSchema(BaseModel):
    combo: str
    voltron: str
    control: str
    stax_taxes: str
    aristocrats: str
    spellslinger: str
    storm: str
    go_wide_tokens: str
    tribal_kindred: str
    aggro_combats: str
    burn_slug: str
    group_hug_politics: str
    pillowfort: str
    reanimator: str
    landfall: str
    lands_matter: str
    stompy: str
    blink_flicker: str
    artifacts: str
    enchantments: str
    superfriends: str
    wheels_discard: str
    counters: str
    theft_clones_aikido: str
    cheat_cascade: str
    alt_win: str
    lifegain_drain: str
    mill: str
    tribal_plus: str
    relentless_colony: str

class CardArchetypeScoreSchema(BaseModel):
    card_analysis: str
    reasoning: ArchetypeReasoningSchema
    combo: int
    voltron: int
    control: int
    stax_taxes: int
    aristocrats: int
    spellslinger: int
    storm: int
    go_wide_tokens: int
    tribal_kindred: int
    aggro_combats: int
    burn_slug: int
    group_hug_politics: int
    pillowfort: int
    reanimator: int
    landfall: int
    lands_matter: int
    stompy: int
    blink_flicker: int
    artifacts: int
    enchantments: int
    superfriends: int
    wheels_discard: int
    counters: int
    theft_clones_aikido: int
    cheat_cascade: int
    alt_win: int
    lifegain_drain: int
    mill: int
    tribal_plus: int
    relentless_colony: int

ARCHETYPE_SCHEMA = {
    "type": "object",
    "properties": {
        "card_analysis": {"type": "string"},
        "reasoning": {
            "type": "object",
            "properties": {
                "combo": {"type": "string"},
                "voltron": {"type": "string"},
                "control": {"type": "string"},
                "stax_taxes": {"type": "string"},
                "aristocrats": {"type": "string"},
                "spellslinger": {"type": "string"},
                "storm": {"type": "string"},
                "go_wide_tokens": {"type": "string"},
                "tribal_kindred": {"type": "string"},
                "aggro_combats": {"type": "string"},
                "burn_slug": {"type": "string"},
                "group_hug_politics": {"type": "string"},
                "pillowfort": {"type": "string"},
                "reanimator": {"type": "string"},
                "landfall": {"type": "string"},
                "lands_matter": {"type": "string"},
                "stompy": {"type": "string"},
                "blink_flicker": {"type": "string"},
                "artifacts": {"type": "string"},
                "enchantments": {"type": "string"},
                "superfriends": {"type": "string"},
                "wheels_discard": {"type": "string"},
                "counters": {"type": "string"},
                "theft_clones_aikido": {"type": "string"},
                "cheat_cascade": {"type": "string"},
                "alt_win": {"type": "string"},
                "lifegain_drain": {"type": "string"},
                "mill": {"type": "string"},
                "tribal_plus": {"type": "string"},
                "relentless_colony": {"type": "string"},
            },
            "required": [
                "combo",
                "voltron",
                "control",
                "stax_taxes",
                "aristocrats",
                "spellslinger",
                "storm",
                "go_wide_tokens",
                "tribal_kindred",
                "aggro_combats",
                "burn_slug",
                "group_hug_politics",
                "pillowfort",
                "reanimator",
                "landfall",
                "lands_matter",
                "stompy",
                "blink_flicker",
                "artifacts",
                "enchantments",
                "superfriends",
                "wheels_discard",
                "counters",
                "theft_clones_aikido",
                "cheat_cascade",
                "alt_win",
                "lifegain_drain",
                "mill",
                "tribal_plus",
                "relentless_colony",
            ],
        },
        "combo": {"type": "integer"},
        "voltron": {"type": "integer"},
        "control": {"type": "integer"},
        "stax_taxes": {"type": "integer"},
        "aristocrats": {"type": "integer"},
        "spellslinger": {"type": "integer"},
        "storm": {"type": "integer"},
        "go_wide_tokens": {"type": "integer"},
        "tribal_kindred": {"type": "integer"},
        "aggro_combats": {"type": "integer"},
        "burn_slug": {"type": "integer"},
        "group_hug_politics": {"type": "integer"},
        "pillowfort": {"type": "integer"},
        "reanimator": {"type": "integer"},
        "landfall": {"type": "integer"},
        "lands_matter": {"type": "integer"},
        "stompy": {"type": "integer"},
        "blink_flicker": {"type": "integer"},
        "artifacts": {"type": "integer"},
        "enchantments": {"type": "integer"},
        "superfriends": {"type": "integer"},
        "wheels_discard": {"type": "integer"},
        "counters": {"type": "integer"},
        "theft_clones_aikido": {"type": "integer"},
        "cheat_cascade": {"type": "integer"},
        "alt_win": {"type": "integer"},
        "lifegain_drain": {"type": "integer"},
        "mill": {"type": "integer"},
        "tribal_plus": {"type": "integer"},
        "relentless_colony": {"type": "integer"},
    },
    "required": [
        "card_analysis",
        "reasoning",
        "combo",
        "voltron",
        "control",
        "stax_taxes",
        "aristocrats",
        "spellslinger",
        "storm",
        "go_wide_tokens",
        "tribal_kindred",
        "aggro_combats",
        "burn_slug",
        "group_hug_politics",
        "pillowfort",
        "reanimator",
        "landfall",
        "lands_matter",
        "stompy",
        "blink_flicker",
        "artifacts",
        "enchantments",
        "superfriends",
        "wheels_discard",
        "counters",
        "theft_clones_aikido",
        "cheat_cascade",
        "alt_win",
        "lifegain_drain",
        "mill",
        "tribal_plus",
        "relentless_colony",
    ],
}