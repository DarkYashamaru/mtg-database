# backend/services/ai/classification/get_card_archetype_score.py

import json
from pathlib import Path

import requests

from models.public_schemas import CardSchema
from pydantic import BaseModel


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3:14b"


PROMPT_PATH = Path("D:/Repositories/mtg-database/backend/services/ai/classification/prompts/system_prompt.md")

class ArchetypeReasoningSchema(BaseModel):
    aggro: str
    control: str
    combo: str
    group_hug: str
    group_slug: str
    chaos: str
    goodstuff: str

class CardArchetypeScoreSchema(BaseModel):
    aggro: int
    control: int
    combo: int
    group_hug: int
    group_slug: int
    chaos: int
    goodstuff: int

    reasoning: ArchetypeReasoningSchema


ARCHETYPE_SCHEMA = {
    "type": "object",
    "properties": {
        "aggro": {"type": "integer"},
        "control": {"type": "integer"},
        "combo": {"type": "integer"},
        "group_hug": {"type": "integer"},
        "group_slug": {"type": "integer"},
        "chaos": {"type": "integer"},
        "goodstuff": {"type": "integer"},
        "reasoning": {
            "type": "object",
            "properties": {
                "aggro": {"type": "string"},
                "control": {"type": "string"},
                "combo": {"type": "string"},
                "group_hug": {"type": "string"},
                "group_slug": {"type": "string"},
                "chaos": {"type": "string"},
                "goodstuff": {"type": "string"},
            },
            "required": [
                "aggro",
                "control",
                "combo",
                "group_hug",
                "group_slug",
                "chaos",
                "goodstuff",
            ],
        },
    },
    "required": [
        "aggro",
        "control",
        "combo",
        "group_hug",
        "group_slug",
        "chaos",
        "goodstuff",
        "reasoning",
    ],
}


def _load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def get_card_archetype_score(card: CardSchema,) -> CardArchetypeScoreSchema:

    system_prompt = _load_system_prompt()

    prompt = (
        "Classify the following MTG card.\n\n"
        f"{card.model_dump_json(indent=2)}"
    )

    print(prompt)

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "system": system_prompt,
            "prompt": prompt,
            "stream": False,
            "format": ARCHETYPE_SCHEMA,
            "options": {
                "temperature": 0.1,
            },
        },
        timeout=300,
    )

    response.raise_for_status()

    data = response.json()

    print(data["response"])

    return CardArchetypeScoreSchema.model_validate_json(
        data["response"]
    )