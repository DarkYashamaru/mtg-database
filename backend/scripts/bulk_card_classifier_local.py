import argparse
import json
import re
import sys
import time
from pathlib import Path
from sqlalchemy.orm import Session
from tools.logger import logger

# Ensure the backend root is in the python path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from database.create_database import create_database
from database.session import get_db
from models.public_schemas import card_to_schema
from services.ai.classification.get_card_archetype_score_local import (
    get_card_archetype_score,
)
# Reusing your database loading utilities
from scripts.classify_cards import (
    direct_tag_ids_for_cards,
    load_card_by_name,
    load_inherited_tags_by_direct_id,
)

RATE_LIMIT_WAIT_RE = re.compile(
    r"(?:please try again in|retry after)\s+([0-9]+(?:\.[0-9]+)?)\s*(?:s|sec|seconds?)",
    re.IGNORECASE,
)
MAX_RETRIES = 10

DEFAULT_INPUT_FILE = ROOT / "data" / "my_collection.txt"
DEFAULT_JSON_OUTPUT = ROOT / "data" / "card_classification.json"


def extract_rate_limit_wait(error: Exception) -> float | None:
    message = str(error)

    match = re.search(
        r"try again in\s+"
        r"(?:(\d+)h)?"
        r"(?:(\d+)m)?"
        r"([0-9]+(?:\.[0-9]+)?)s",
        message,
        re.IGNORECASE,
    )

    if not match:
        return None

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = float(match.group(3))

    return hours * 3600 + minutes * 60 + seconds


def parse_bulk_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bulk classify MTG cards from a text list into a JSON cache."
    )
    parser.add_argument(
        "--input",
        type=str,
        default=str(DEFAULT_INPUT_FILE),
        help="Path to the text file containing the card list (e.g., deck export).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(DEFAULT_JSON_OUTPUT),
        help="Path to the JSON file where results are cached.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay in seconds between requests to help avoid rate limits.",
    )
    return parser.parse_args()


def parse_card_line(line: str) -> str | None:
    """Removes card counts (e.g., '1 Adarkar Wastes' -> 'Adarkar Wastes') and cleans whitespace."""
    cleaned = line.strip()
    if not cleaned or cleaned.startswith("#"):
        return None

    # Matches optional digits followed by spaces, capturing the rest as the card name
    match = re.match(r"^(?:\d+\s+)?(.*)$", cleaned)
    return match.group(1).strip() if match else None


def load_json_cache(filepath: Path) -> dict:
    """Loads existing classifications or returns an empty dict if the file doesn't exist."""
    if filepath.exists():
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.info(f"Warning: {filepath.name} was corrupted or empty. Starting fresh.")
            return {}
    return {}


def save_json_cache(filepath: Path, data: dict):
    """Saves the cache immediately to disk."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main() -> int:
    args = parse_bulk_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        logger.info(f"Error: Input file not found at {input_path}")
        return 1

    # 1. Parse unique card names from the file
    card_names: list[str] = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            name = parse_card_line(line)
            if name and name not in card_names:
                card_names.append(name)

    logger.info(f"Found {len(card_names)} unique card names in {input_path.name}.")

    # 2. Load existing progress from JSON
    cache = load_json_cache(output_path)
    logger.info(f"Loaded {len(cache)} already-classified cards from cache.")

    # Filter out what's already done
    queue = [name for name in card_names if name not in cache]
    logger.info(f"Cards remaining to classify: {len(queue)}")

    if not queue:
        logger.info("All cards are already classified!")
        return 0

    # 3. Initialize Database
    create_database()
    db: Session = next(get_db())

    processed_count = 0

    try:
        for i, name in enumerate(queue, 1):
            logger.info(f"\n[{i}/{len(queue)}] Processing: {name}...", end="", flush=True)

            # Retrieve from DB
            try:
                card = load_card_by_name(db, name)
            except ValueError as ve:
                logger.info(f"\n  Skipping due to DB error: {ve}")
                cache[name] = {"error": f"Database resolution error: {str(ve)}"}
                save_json_cache(output_path, cache)
                continue

            if card is None:
                logger.info("\n  Skipping: Card not found in local database.")
                cache[name] = {"error": "Not found in local database"}
                save_json_cache(output_path, cache)
                continue

            # Build Schema payload
            inherited_tags = load_inherited_tags_by_direct_id(
                db, direct_tag_ids_for_cards([card])
            )
            schema = card_to_schema(card, inherited_tags)

            # Hit the LLM via Litellm/Groq with retries
            attempt = 0
            while attempt < MAX_RETRIES:
                try:
                    result = get_card_archetype_score(schema)

                    # Store the Pydantic data back into our cache dictionary
                    cache[schema.name] = result.model_dump(exclude_defaults=True)

                    # If the queried name was slightly different (e.g. casing), link it too
                    if name != schema.name:
                        cache[name] = {"alias_to": schema.name}

                    # Save immediately to the JSON file
                    save_json_cache(output_path, cache)
                    logger.info(" Success!")
                    processed_count += 1

                    # Polite pause to mitigate rapid rate-limits
                    if args.delay > 0:
                        time.sleep(args.delay)

                    break

                except Exception as llm_error:
                    retry_after = extract_rate_limit_wait(llm_error)

                    if retry_after is not None:
                        attempt += 1
                        wait_time = retry_after + 0.5  # small safety buffer

                        logger.info(
                            f"\n  Rate limit hit "
                            f"(attempt {attempt}/{MAX_RETRIES}). "
                            f"Waiting {wait_time:.2f}s and retrying..."
                        )

                        time.sleep(wait_time)
                        continue

                    logger.info("\n  Skipping this card due to unexpected LLM error.")
                    logger.info(f"  Details: {llm_error}")
                    logger.info(f"  Error: {llm_error}")
                    break

            else:
                logger.info(
                    f"\n  Rate limit retries exceeded after {MAX_RETRIES} attempts. "
                    f"Skipping card."
                )
                cache[name] = {
                    "error": f"Rate limit retries exceeded ({MAX_RETRIES})"
                }
                save_json_cache(output_path, cache)

    finally:
        db.close()

    logger.info(f"\nRun complete. Processed {processed_count} cards.")
    return 0


if __name__ == "__main__":
    sys.exit(main())