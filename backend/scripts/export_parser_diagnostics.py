from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from oracle_card_parser import load_cards, parse_face


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = ROOT / "parser_diagnostics.json"
TOP_N = 200
SAMPLE_LIMIT = 5


def iter_custom_effects(parsed_face: dict[str, Any]) -> list[str]:
    texts: list[str] = []

    for bucket in ("triggered", "activated", "static_abilities"):
        for ability in parsed_face.get(bucket, []):
            for effect in ability.get("effects", []):
                if effect.get("action") == "custom_effect":
                    text = effect.get("text")
                    if text:
                        texts.append(text)

    return texts


def iter_custom_triggers(parsed_face: dict[str, Any]) -> list[str]:
    texts: list[str] = []

    for ability in parsed_face.get("triggered", []):
        trigger = ability.get("trigger", {})
        if trigger.get("type") == "custom" and trigger.get("text"):
            texts.append(trigger["text"])

    return texts


def build_diagnostics() -> dict[str, Any]:
    cards = load_cards()

    custom_effect_counts: Counter[str] = Counter()
    custom_effect_samples: dict[str, list[dict[str, str]]] = defaultdict(list)

    custom_trigger_counts: Counter[str] = Counter()
    custom_trigger_samples: dict[str, list[dict[str, str]]] = defaultdict(list)

    total_faces = 0
    total_custom_effect_instances = 0
    total_custom_trigger_instances = 0

    for card in cards:
        for face in card["faces"]:
            total_faces += 1
            parsed_face = parse_face(face)

            for text in iter_custom_effects(parsed_face):
                custom_effect_counts[text] += 1
                total_custom_effect_instances += 1
                if len(custom_effect_samples[text]) < SAMPLE_LIMIT:
                    custom_effect_samples[text].append(
                        {
                            "card_name": card["name"],
                            "face_name": parsed_face["name"],
                        }
                    )

            for text in iter_custom_triggers(parsed_face):
                custom_trigger_counts[text] += 1
                total_custom_trigger_instances += 1
                if len(custom_trigger_samples[text]) < SAMPLE_LIMIT:
                    custom_trigger_samples[text].append(
                        {
                            "card_name": card["name"],
                            "face_name": parsed_face["name"],
                        }
                    )

    top_custom_effects = [
        {
            "text": text,
            "count": count,
            "samples": custom_effect_samples[text],
        }
        for text, count in custom_effect_counts.most_common(TOP_N)
    ]

    top_custom_triggers = [
        {
            "text": text,
            "count": count,
            "samples": custom_trigger_samples[text],
        }
        for text, count in custom_trigger_counts.most_common(TOP_N)
    ]

    return {
        "summary": {
            "total_cards": len(cards),
            "total_faces": total_faces,
            "custom_effect_instances": total_custom_effect_instances,
            "unique_custom_effects": len(custom_effect_counts),
            "custom_trigger_instances": total_custom_trigger_instances,
            "unique_custom_triggers": len(custom_trigger_counts),
            "top_n": TOP_N,
            "sample_limit": SAMPLE_LIMIT,
        },
        "custom_effects": top_custom_effects,
        "custom_triggers": top_custom_triggers,
    }


def export_diagnostics() -> Path:
    diagnostics = build_diagnostics()
    OUTPUT_PATH.write_text(
        json.dumps(diagnostics, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    return OUTPUT_PATH


if __name__ == "__main__":
    path = export_diagnostics()
    print(f"Wrote parser diagnostics to {path}")
