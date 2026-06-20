# card_classifier.py
from pathlib import Path
import litellm
from services.ai.llm_factory import get_llm_config 
from models.public_schemas import CardSchema
from models.llm_schemas import CardArchetypeScoreSchema
import json
from tools.logger import logger

PROMPT_PATH = Path("D:/Repositories/mtg-database/backend/services/ai/classification/prompts/system_prompt.md")
litellm._turn_on_debug()


def _load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")

def clean_card_for_llm(raw_card_dict):
    cleaned = {
        "name": raw_card_dict.get("name"),
        "tags": {
            "direct": [t["slug"] for t in raw_card_dict.get("tags", {}).get("direct", [])],
            "inherited": [t["slug"] for t in raw_card_dict.get("tags", {}).get("inherited", [])]
        },
        "faces": [
            {
                "name": f.get("name"),
                "mana_cost": f.get("mana_cost"),
                "oracle_text": f.get("oracle_text"),
                "card_types": f.get("card_types"),
                "subtypes": f.get("subtypes")
            }
            for f in raw_card_dict.get("faces", [])
        ],
        "keywords": [k.get("label") for k in raw_card_dict.get("keywords", [])]
    }
    return cleaned


def get_card_archetype_score(card: CardSchema) -> CardArchetypeScoreSchema:
    # 1. Prepare standard payload instructions

    cleaned_dict = clean_card_for_llm(card.model_dump())
    card_json = json.dumps(cleaned_dict, ensure_ascii=False)

    logger.info("Cleaned Payload Sent to LLM:")
    logger.info(card_json)

    system_prompt = _load_system_prompt()
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user", 
            "content": f"Classify the following MTG card.\n\n{card_json}"
        }
    ]

    # 2. Grab the environment configuration dictionary
    completion_kwargs = get_llm_config()

    completion_kwargs.update({
            "messages": messages,
            "temperature": 0.1,
            "response_format": CardArchetypeScoreSchema,
            "timeout": 600,
        })

    # 3. Merge runtime execution parameters into the configuration dictionary
    completion_kwargs.update({
        "messages": messages,
        "temperature": 0.1,
        "response_format": CardArchetypeScoreSchema,
    })

    # 4. Fire the request
    logger.info(f"Executing request with target model target: {completion_kwargs.get('model')}")
    response = litellm.completion(**completion_kwargs)

    # 5. Extract and validate string responses directly into your target schema
    content = response.choices[0].message.content
    return CardArchetypeScoreSchema.model_validate_json(content)