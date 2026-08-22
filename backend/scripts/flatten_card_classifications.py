from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from backend.database.classification_session import CLASSIFICATION_DATABASE_PATH, classification_session_scope
    from backend.database.create_classification_database import create_classification_database
    from backend.models.card_classification import CardClassification, ParsedAbility, ParsedEffect, ParsedFace
except ModuleNotFoundError:
    from database.classification_session import CLASSIFICATION_DATABASE_PATH, classification_session_scope
    from database.create_classification_database import create_classification_database
    from models.card_classification import CardClassification, ParsedAbility, ParsedEffect, ParsedFace


ABILITY_TYPES = ("triggered", "activated", "static_abilities")


@dataclass
class EffectNode:
    path: str
    parent_path: str | None
    payload: dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Flatten parsed card payloads from card_classifications into relational tables.",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=CLASSIFICATION_DATABASE_PATH,
        help="Path to the card classification sqlite database.",
    )
    parser.add_argument(
        "--export-scope",
        choices=("cards", "commanders", "all"),
        default="all",
        help="Which exported scope to flatten.",
    )
    return parser.parse_args()


def json_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True)


def iter_effect_nodes(node: Any, path: str = "root", parent_path: str | None = None) -> list[EffectNode]:
    nodes: list[EffectNode] = []

    if isinstance(node, dict):
        current_parent_path = parent_path
        if isinstance(node.get("action"), str):
            nodes.append(EffectNode(path=path, parent_path=parent_path, payload=node))
            current_parent_path = path

        for key, value in node.items():
            child_path = f"{path}.{key}"
            nodes.extend(iter_effect_nodes(value, child_path, current_parent_path))
        return nodes

    if isinstance(node, list):
        for index, value in enumerate(node):
            child_path = f"{path}[{index}]"
            nodes.extend(iter_effect_nodes(value, child_path, parent_path))
    return nodes


def flatten_payload_record(record: CardClassification, db: Session) -> tuple[int, int, int]:
    payload = json.loads(record.payload_json)
    face_count = 0
    ability_count = 0
    effect_count = 0

    for face_index, face_payload in enumerate(payload.get("faces", [])):
        face = ParsedFace(
            export_scope=record.export_scope,
            oracle_id=record.oracle_id,
            face_index=face_index,
            name=face_payload.get("name", ""),
            type_line=face_payload.get("type_line", ""),
            oracle_text=face_payload.get("oracle_text") or "",
            face_json=json_dumps(face_payload),
        )
        db.add(face)
        db.flush()
        face_count += 1

        for ability_type in ABILITY_TYPES:
            for ability_index, ability_payload in enumerate(face_payload.get(ability_type, [])):
                ability = ParsedAbility(
                    face_id=face.id,
                    ability_type=ability_type,
                    ability_index=ability_index,
                    raw_text=ability_payload.get("raw_text"),
                    trigger_json=json_dumps(ability_payload["trigger"]) if "trigger" in ability_payload else None,
                    cost_json=json_dumps(ability_payload["cost"]) if "cost" in ability_payload else None,
                    condition_json=json_dumps(ability_payload["condition"]) if "condition" in ability_payload else None,
                    mode_selection_json=json_dumps(ability_payload["mode_selection"]) if "mode_selection" in ability_payload else None,
                    ability_json=json_dumps(ability_payload),
                )
                db.add(ability)
                db.flush()
                ability_count += 1

                path_to_effect_id: dict[str, int] = {}
                for effect_index, node in enumerate(iter_effect_nodes(ability_payload)):
                    target = node.payload.get("target")
                    parsed_effect = ParsedEffect(
                        ability_id=ability.id,
                        parent_effect_id=path_to_effect_id.get(node.parent_path),
                        effect_index=effect_index,
                        path=node.path,
                        action=node.payload["action"],
                        target_json=json_dumps(target) if target is not None else None,
                        target_signature=json_dumps(target) if target is not None else None,
                        effect_json=json_dumps(node.payload),
                    )
                    db.add(parsed_effect)
                    db.flush()
                    path_to_effect_id[node.path] = parsed_effect.id
                    effect_count += 1

    return face_count, ability_count, effect_count


def flatten_card_classifications(
    db: Session,
    export_scope: str = "all",
) -> tuple[int, int, int, int]:
    scopes = ("cards", "commanders") if export_scope == "all" else (export_scope,)

    face_ids_stmt = select(ParsedFace.id).where(ParsedFace.export_scope.in_(scopes))
    db.execute(
        delete(ParsedEffect).where(
            ParsedEffect.ability_id.in_(
                select(ParsedAbility.id).where(
                    ParsedAbility.face_id.in_(face_ids_stmt)
                )
            )
        )
    )
    db.execute(
        delete(ParsedAbility).where(
            ParsedAbility.face_id.in_(face_ids_stmt)
        )
    )
    db.execute(delete(ParsedFace).where(ParsedFace.export_scope.in_(scopes)))
    db.flush()

    stmt = select(CardClassification).where(CardClassification.export_scope.in_(scopes)).order_by(
        CardClassification.export_scope,
        CardClassification.name,
    )
    records = list(db.execute(stmt).scalars())

    card_count = 0
    face_count = 0
    ability_count = 0
    effect_count = 0

    for record in records:
        card_count += 1
        faces, abilities, effects = flatten_payload_record(record, db)
        face_count += faces
        ability_count += abilities
        effect_count += effects

    return card_count, face_count, ability_count, effect_count


def main() -> int:
    args = parse_args()
    create_classification_database(args.database)

    with classification_session_scope(args.database) as db:
        card_count, face_count, ability_count, effect_count = flatten_card_classifications(
            db,
            export_scope=args.export_scope,
        )

    print(
        "Flattened "
        f"{card_count} cards, {face_count} faces, {ability_count} abilities, {effect_count} effects "
        f"into {args.database}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
