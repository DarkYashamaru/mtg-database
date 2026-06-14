import json
import os
from pathlib import Path
from typing import Any

import requests

from models.public_schemas import CardSchema
from pydantic import BaseModel, ConfigDict, Field, ValidationError


DEFAULT_OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434/api/generate",
)
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:14b")
PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "system_prompt.md"

Score = int


class ArchetypeReasoningSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    combo: str = Field(min_length=3)
    voltron: str = Field(min_length=3)
    control: str = Field(min_length=3)
    stax: str = Field(min_length=3)
    aristocrats: str = Field(min_length=3)
    spellslinger_storm: str = Field(min_length=3)
    go_wide_token_swarm: str = Field(min_length=3)
    tribal_kindred: str = Field(min_length=3)
    aggro: str = Field(min_length=3)
    group_hug_politics: str = Field(min_length=3)
    reanimator: str = Field(min_length=3)
    landfall: str = Field(min_length=3)
    stompy: str = Field(min_length=3)


class CardArchetypeScoreSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    combo: Score = Field(ge=0, le=100)
    voltron: Score = Field(ge=0, le=100)
    control: Score = Field(ge=0, le=100)
    stax: Score = Field(ge=0, le=100)
    aristocrats: Score = Field(ge=0, le=100)
    spellslinger_storm: Score = Field(ge=0, le=100)
    go_wide_token_swarm: Score = Field(ge=0, le=100)
    tribal_kindred: Score = Field(ge=0, le=100)
    aggro: Score = Field(ge=0, le=100)
    group_hug_politics: Score = Field(ge=0, le=100)
    reanimator: Score = Field(ge=0, le=100)
    landfall: Score = Field(ge=0, le=100)
    stompy: Score = Field(ge=0, le=100)

    reasoning: ArchetypeReasoningSchema


ARCHETYPE_SCHEMA = CardArchetypeScoreSchema.model_json_schema()


def _load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _tag_payload(tags: list[Any]) -> list[dict[str, str | None]]:
    return [
        {
            "slug": tag.slug,
            "description": tag.description,
        }
        for tag in tags
    ]


def _card_evidence_payload(card: CardSchema) -> dict[str, Any]:
    """Keep model input focused on gameplay evidence, not database noise."""
    return {
        "name": card.name,
        "cmc": card.cmc,
        "layout": card.layout,
        "commander_legal": card.commander_legal,
        "color_identity": [
            color.symbol
            for color in card.color_identity
        ],
        "keywords": [
            keyword.label
            for keyword in card.keywords
        ],
        "faces": [
            {
                "name": face.name,
                "mana_cost": face.mana_cost,
                "supertypes": face.supertypes,
                "card_types": face.card_types,
                "subtypes": face.subtypes,
                "oracle_text": face.oracle_text,
            }
            for face in card.faces
        ],
        "tags": {
            "direct": _tag_payload(card.tags.direct),
            "inherited": _tag_payload(card.tags.inherited),
        },
    }


def _build_prompt(card: CardSchema) -> str:
    evidence_json = json.dumps(
        _card_evidence_payload(card),
        ensure_ascii=False,
        indent=2,
    )

    return (
        "Classify this single MTG Commander card using only the evidence below.\n"
        "Use 0 when an archetype has no direct support from the card.\n"
        "Keep each reasoning value to one short evidence-based sentence.\n\n"
        f"Card evidence:\n{evidence_json}"
    )


def get_card_archetype_score(
    card: CardSchema,
    *,
    model: str = DEFAULT_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    timeout_seconds: int = 300,
    verbose: bool = False,
) -> CardArchetypeScoreSchema:

    system_prompt = _load_system_prompt()
    prompt = _build_prompt(card)

    if verbose:
        print(prompt)

    response = requests.post(
        ollama_url,
        json={
            "model": model,
            "system": system_prompt,
            "prompt": prompt,
            "stream": False,
            "format": ARCHETYPE_SCHEMA,
            "options": {
                "temperature": 0,
                "top_p": 0.9,
            },
        },
        timeout=timeout_seconds,
    )

    response.raise_for_status()

    data = response.json()
    raw_response = data["response"]

    if verbose:
        print(raw_response)

    try:
        return CardArchetypeScoreSchema.model_validate_json(raw_response)
    except ValidationError as exc:
        raise ValueError(
            "Ollama returned JSON that did not match the archetype schema: "
            f"{raw_response}"
        ) from exc
