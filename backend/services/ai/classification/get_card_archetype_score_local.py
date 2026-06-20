from pathlib import Path
import json
import re
import requests

from models.public_schemas import CardSchema
from models.llm_schemas import CardArchetypeScoreSchema

PROMPT_PATH = Path(
    "D:/Repositories/mtg-database/backend/services/ai/classification/prompts/system_prompt.md"
)

# The exact endpoint exposed by your running llama-server.exe instance
LLAMA_SERVER_URL = "http://localhost:8080/v1/chat/completions"


def _load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def clean_card_for_llm(raw_card_dict):
    return {
        "name": raw_card_dict.get("name"),
        "tags": {
            "direct": [
                t["slug"]
                for t in raw_card_dict.get("tags", {}).get("direct", [])
            ],
            "inherited": [
                t["slug"]
                for t in raw_card_dict.get("tags", {}).get("inherited", [])
            ],
        },
        "faces": [
            {
                "name": f.get("name"),
                "mana_cost": f.get("mana_cost"),
                "oracle_text": f.get("oracle_text"),
                "card_types": f.get("card_types"),
                "subtypes": f.get("subtypes"),
            }
            for f in raw_card_dict.get("faces", [])
        ],
        "keywords": [
            k.get("label")
            for k in raw_card_dict.get("keywords", [])
        ],
    }


def extract_pure_json(text: str) -> str:
    """
    Robust JSON mining utility. Strips out any leaking <think> blocks or
    Markdown backticks left behind by local reasoning models.
    """

    # Remove any thinking blocks if they leaked directly into the content string
    text = re.sub(
        r"<think>.*?</think>",
        "",
        text,
        flags=re.DOTALL,
    )

    # Check for Markdown fenced code blocks containing JSON
    markdown_match = re.search(
        r"```(?:json)?\s*(\{.*?\})\s*```",
        text,
        re.DOTALL,
    )

    if markdown_match:
        return markdown_match.group(1).strip()

    # Fallback to capturing the outermost raw curly braces boundaries
    braces_match = re.search(
        r"\{.*\}",
        text,
        re.DOTALL,
    )

    if braces_match:
        return braces_match.group(0).strip()

    return text.strip()


def get_card_archetype_score(
    card: CardSchema,
) -> CardArchetypeScoreSchema:

    # 1. Standardize and clean input card payload
    cleaned_dict = clean_card_for_llm(card.model_dump())
    card_json = json.dumps(
        cleaned_dict,
        ensure_ascii=False,
    )

    print("\n--- Cleaned Payload Sent to LLM ---")
    print(card_json)

    system_prompt = _load_system_prompt()

    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": (
                f"Classify the following MTG card.\n\n"
                f"{card_json}"
            ),
        },
    ]

    # 2. Build the optimized llama-server direct payload
    # By omitting a hard 'response_format' grammar rule, we allow the model
    # to safely execute its <think> process first, preventing internal
    # generation lockups.
    payload = {
        "messages": messages,
        "temperature": 0.0,
        "top_p": 0.95,
        "frequency_penalty": 1.05,
        "max_tokens": 8192,
        "think": False,
        "cache_prompt": True,
        "response_format": {"type": "json_object"},
        "json_schema": CardArchetypeScoreSchema.model_json_schema()
    }

    print("Firing direct HTTP request to llama-server context window...")

    # 3. Fire the request directly over native HTTP (no abstraction layer)
    # 600-second timeout to accommodate heavy multi-archetype evaluation
    # thinking periods
    response = requests.post(
        LLAMA_SERVER_URL,
        json=payload,
        timeout=600,
    )

    response.raise_for_status()

    response_data = response.json()
    message_obj = response_data["choices"][0]["message"]

    # 4. Extract and print internal thinking steps if available
    reasoning_content = message_obj.get("reasoning_content", "")
    content = message_obj.get("content", "")

    if reasoning_content:
        print("\n=== QWEN INTERNAL REASONING ===")
        print(reasoning_content.strip())
        print("================================\n")

    elif "<think>" in content:
        think_match = re.search(
            r"<think>(.*?)</think>",
            content,
            re.DOTALL,
        )

        if think_match:
            print("\n=== QWEN INTERNAL REASONING ===")
            print(think_match.group(1).strip())
            print("================================\n")

    # 5. Mine out the final JSON block and pass it to your Pydantic Schema
    clean_json_string = extract_pure_json(content)

    try:
        return CardArchetypeScoreSchema.model_validate_json(
            clean_json_string
        )

    except Exception as e:
        print("\n!!! Pydantic Parsing Failed !!!")
        print("Raw text returned by model that caused failure:")
        print(content)
        print("\nExtracted JSON:")
        print(clean_json_string)
        raise e