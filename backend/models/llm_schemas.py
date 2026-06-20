
from pydantic import BaseModel, Field

class CardArchetypeScoreSchema(BaseModel):
    card_analysis: str
    
    # Setting default=0 allows Pydantic to recognize it as the fallback
    combo: int = Field(default=0)
    voltron: int = Field(default=0)
    control: int = Field(default=0)
    stax_taxes: int = Field(default=0)
    aristocrats: int = Field(default=0)
    spellslinger: int = Field(default=0)
    storm: int = Field(default=0)
    go_wide_tokens: int = Field(default=0)
    tribal_kindred: int = Field(default=0)
    aggro_combats: int = Field(default=0)
    burn_slug: int = Field(default=0)
    group_hug_politics: int = Field(default=0)
    pillowfort: int = Field(default=0)
    reanimator: int = Field(default=0)
    landfall: int = Field(default=0)
    lands_matter: int = Field(default=0)
    stompy: int = Field(default=0)
    blink_flicker: int = Field(default=0)
    artifacts: int = Field(default=0)
    enchantments: int = Field(default=0)
    superfriends: int = Field(default=0)
    wheels_discard: int = Field(default=0)
    counters: int = Field(default=0)
    theft_clones_aikido: int = Field(default=0)
    cheat_cascade: int = Field(default=0)
    alt_win: int = Field(default=0)
    lifegain_drain: int = Field(default=0)
    mill: int = Field(default=0)
    tribal_plus: int = Field(default=0)
    relentless_colony: int = Field(default=0)

ARCHETYPE_SCHEMA = {
    "type": "object",
    "properties": {
        "card_analysis": {"type": "string"},
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