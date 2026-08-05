from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = ROOT / "backend" / "cards.sqlite"
COMMANDER_OUTPUT_DIR = ROOT / "commanders"
CARD_OUTPUT_DIR = ROOT / "cards"

NUMBER_WORDS = {
    "a": 1,
    "an": 1,
    "one": 1,
    "first": 1,
    "two": 2,
    "second": 2,
    "three": 3,
    "third": 3,
    "four": 4,
    "fourth": 4,
    "five": 5,
    "fifth": 5,
    "six": 6,
    "sixth": 6,
    "seven": 7,
    "seventh": 7,
    "eight": 8,
    "eighth": 8,
    "nine": 9,
    "ninth": 9,
    "ten": 10,
    "tenth": 10,
    "x": "X",
}

KEYWORDS = {
    "ascend",
    "aftermath",
    "bargain",
    "cascade",
    "changeling",
    "convoke",
    "devoid",
    "deathtouch",
    "delve",
    "defender",
    "double strike",
    "exalted",
    "fear",
    "first strike",
    "flash",
    "flying",
    "horsemanship",
    "haste",
    "hexproof",
    "indestructible",
    "infect",
    "intimidate",
    "islandwalk",
    "lifelink",
    "menace",
    "myriad",
    "nightbound",
    "daybound",
    "persist",
    "partner",
    "prowess",
    "reach",
    "rebound",
    "shadow",
    "shroud",
    "soulbond",
    "split second",
    "storm",
    "swampwalk",
    "undying",
    "trample",
    "vigilance",
}

COLOR_WORDS = {"white", "blue", "black", "red", "green"}
ARTICLE_WORDS = {"a", "an"}
CARD_TYPE_WORDS = {
    "artifact",
    "artifacts",
    "battle",
    "battles",
    "creature",
    "creatures",
    "enchantment",
    "enchantments",
    "land",
    "lands",
    "planeswalker",
    "planeswalkers",
    "instant",
    "instants",
    "sorcery",
    "sorceries",
}

ABILITY_LABEL_RE = re.compile(r"^[A-Z][A-Za-z' ,\-]+ [—-] ")
SAGA_REMINDER_PREFIX = "(as this saga enters and after your draw step, add a lore counter"


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def filename_for_card(name: str) -> str:
    safe = name.replace("//", " - ")
    safe = re.sub(r'[<>:"/\\|?*]', "-", safe)
    safe = re.sub(r"\s+", " ", safe).strip()
    return f"{safe}.json"


def parse_number(token: str) -> int | str | None:
    value = token.strip().lower().strip(".")
    if value.startswith("{") and value.endswith("}"):
        inner = value[1:-1]
        return int(inner) if inner.isdigit() else inner.upper()
    if value.isdigit():
        return int(value)
    return NUMBER_WORDS.get(value)


def strip_reminder_text(text: str) -> str:
    return re.sub(r"\s*\([^)]*\)", "", text).strip()


def split_abilities(oracle_text: str | None) -> list[str]:
    if not oracle_text:
        return []
    grouped: list[str] = []
    for raw_line in oracle_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("•") and grouped and _is_modal_header_line(grouped[-1]):
            grouped[-1] = f"{grouped[-1]}\n{line}"
            continue
        grouped.append(line)
    return grouped


def _is_modal_header_line(text: str) -> bool:
    first_line = text.splitlines()[0].strip()
    lowered = first_line.lower()
    if re.fullmatch(r"choose .+ [—-]", lowered):
        return True
    return bool(re.search(r"\bchoose .+ [—-]$", lowered))


def parse_modal_block(text: str, card_name: str) -> dict[str, Any] | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return None

    header = lines[0]
    bullets = [line for line in lines[1:] if line.startswith("•")]
    if len(bullets) != len(lines) - 1:
        return None

    lowered = header.lower()
    selection_match = re.search(
        r"choose (?P<count>\w+)(?P<or_both> or both)?(?P<at_random> at random)?\s+[—-]$",
        lowered,
    )
    if not selection_match:
        return None

    choose_count = parse_number(selection_match.group("count")) or selection_match.group("count")
    payload: dict[str, Any] = {
        "mode_selection": {
            "choose_count": choose_count,
            "random": bool(selection_match.group("at_random")),
        },
        "modes": [],
    }
    if selection_match.group("or_both"):
        payload["mode_selection"]["or_both"] = True

    for bullet in bullets:
        option_text = bullet.lstrip("•").strip()
        body = strip_ability_label(option_text)
        payload["modes"].append({
            "raw_text": option_text,
            "effects": parse_effects_text(body, card_name),
        })

    return payload


def parse_saga_chapter_ability(text: str, card_name: str) -> dict[str, Any] | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    header_line = lines[0]
    match = re.fullmatch(r"([IVX,\s]+)\s+[—-]\s+(.+)", normalize_whitespace(header_line))
    if not match:
        return None

    chapter_text = match.group(1).strip()
    effect_text = match.group(2).strip()
    chapters = [part.strip() for part in chapter_text.split(",") if part.strip()]
    if not chapters or not all(re.fullmatch(r"[IVX]+", chapter) for chapter in chapters):
        return None

    ability: dict[str, Any] = {
        "raw_text": text,
        "trigger": {
            "type": "saga_chapter",
            "chapters": chapters,
        },
        "condition": [],
    }
    modal_payload = parse_modal_block("\n".join([effect_text, *lines[1:]]), card_name)
    if modal_payload is not None:
        ability["effects"] = []
        ability.update(modal_payload)
        return ability

    effect_text = strip_ability_label(effect_text)
    ability["effects"] = parse_effects_text(effect_text, card_name)
    return ability


def strip_ability_label(text: str) -> str:
    if " — " in text:
        label, rest = text.split(" — ", 1)
        if label and label[0].isupper():
            lowered = rest.lower()
            if lowered.startswith(("when ", "whenever ", "at ", "during ", "as long as ")):
                return rest.strip()
    if " - " in text:
        label, rest = text.split(" - ", 1)
        lowered = rest.lower()
        if label and lowered.startswith(("when ", "whenever ", "at ", "during ", "as long as ")):
            return rest.strip()
    return text


def split_keyword_clauses(text: str) -> list[str]:
    text = strip_reminder_text(text)
    text = text.replace(";", ",")
    return [part.strip() for part in text.split(",") if part.strip()]


def parse_keyword_clause(clause: str) -> dict[str, Any] | None:
    lowered = clause.lower()

    ward_match = re.fullmatch(r"ward\s+(\{[^}]+\}|\w+)", lowered)
    if ward_match:
        return {
            "keyword": "ward",
            "amount": parse_number(ward_match.group(1)) or ward_match.group(1),
        }

    toxic_match = re.fullmatch(r"toxic\s+(\d+)", lowered)
    if toxic_match:
        return {"keyword": "toxic", "amount": int(toxic_match.group(1))}

    bushido_match = re.fullmatch(r"bushido\s+(\d+)", lowered)
    if bushido_match:
        return {"keyword": "bushido", "amount": int(bushido_match.group(1))}

    backup_match = re.fullmatch(r"backup\s+(\d+)", lowered)
    if backup_match:
        return {"keyword": "backup", "amount": int(backup_match.group(1))}

    mentor_match = re.fullmatch(r"mentor", lowered)
    if mentor_match:
        return {"keyword": "mentor"}

    exploit_match = re.fullmatch(r"exploit", lowered)
    if exploit_match:
        return {"keyword": "exploit"}

    evolve_match = re.fullmatch(r"evolve", lowered)
    if evolve_match:
        return {"keyword": "evolve"}

    flanking_match = re.fullmatch(r"flanking", lowered)
    if flanking_match:
        return {"keyword": "flanking"}

    delve_match = re.fullmatch(r"delve", lowered)
    if delve_match:
        return {"keyword": "delve"}

    cascade_match = re.fullmatch(r"cascade", lowered)
    if cascade_match:
        return {"keyword": "cascade"}

    spree_match = re.fullmatch(r"spree", lowered)
    if spree_match:
        return {"keyword": "spree"}

    wither_match = re.fullmatch(r"wither", lowered)
    if wither_match:
        return {"keyword": "wither"}

    battle_cry_match = re.fullmatch(r"battle cry", lowered)
    if battle_cry_match:
        return {"keyword": "battle_cry"}

    banding_match = re.fullmatch(r"banding", lowered)
    if banding_match:
        return {"keyword": "banding"}

    for_mirrodin_match = re.fullmatch(r"for mirrodin!", lowered)
    if for_mirrodin_match:
        return {"keyword": "for_mirrodin"}

    choose_background_match = re.fullmatch(r"choose a background", lowered)
    if choose_background_match:
        return {"keyword": "choose_a_background"}

    doctors_companion_match = re.fullmatch(r"doctor's companion", lowered)
    if doctors_companion_match:
        return {"keyword": "doctors_companion"}

    living_weapon_match = re.fullmatch(r"living weapon", lowered)
    if living_weapon_match:
        return {"keyword": "living_weapon"}

    protection_match = re.fullmatch(r"protection from ([a-z]+)", lowered)
    if protection_match:
        return {"keyword": "protection", "quality": protection_match.group(1)}

    landwalk_match = re.fullmatch(r"([a-z]+)walk", lowered)
    if landwalk_match and landwalk_match.group(1) in {"forest", "island", "swamp", "mountain", "plains"}:
        return {"keyword": f"{landwalk_match.group(1)}walk"}

    affinity_match = re.fullmatch(r"affinity for ([a-z ]+)", lowered)
    if affinity_match:
        return {"keyword": "affinity", "quality": affinity_match.group(1).replace(" ", "_")}

    cumulative_upkeep_match = re.fullmatch(r"cumulative upkeep (\{[^}]+\})", lowered)
    if cumulative_upkeep_match:
        return {"keyword": "cumulative_upkeep", "cost": cumulative_upkeep_match.group(1)}

    for keyword in sorted(KEYWORDS, key=len, reverse=True):
        if lowered == keyword:
            return {"keyword": keyword}

    return None


def parse_keywords_line(text: str) -> list[dict[str, Any]] | None:
    clauses = split_keyword_clauses(text)
    if not clauses:
        return None

    parsed: list[dict[str, Any]] = []
    for clause in clauses:
        keyword = parse_keyword_clause(clause)
        if keyword is None:
            return None
        parsed.append(keyword)
    return parsed


def normalize_subject(text: str, card_name: str) -> str:
    lowered = text.lower().strip()
    card_name = card_name or ""
    if card_name:
        lowered = lowered.replace(card_name.lower(), "self")
    primary_name = card_name.split("//", 1)[0].split(",", 1)[0].strip().lower()
    if primary_name:
        lowered = re.sub(rf"\b{re.escape(primary_name)}\b", "self", lowered)
    first_word = ""
    first_parts = card_name.split("//", 1)[0].strip().split()
    if first_parts:
        first_word = first_parts[0].lower()
    if first_word:
        lowered = re.sub(rf"\b{re.escape(first_word)}\b", "self", lowered)
    lowered = lowered.replace("this creature", "self")
    lowered = lowered.replace("this spell", "self_spell")
    lowered = lowered.replace(" him", " self")
    lowered = lowered.replace(" her", " self")
    lowered = lowered.replace(" them", " self")
    if lowered in {"him", "her", "them", "it"}:
        lowered = "self"
    lowered = lowered.replace("another ", "another_")
    lowered = lowered.replace(" your ", "_you_control ")
    lowered = lowered.replace(" you control", "_you_control")
    lowered = lowered.replace(" opponents ", "_opponents ")
    lowered = lowered.replace(" opponent controls", "_opponent_controls")
    lowered = lowered.replace(" ", "_")
    lowered = lowered.replace("-", "_")
    lowered = re.sub(r"[^a-z0-9_]+", "", lowered)
    return lowered or "custom"


def parse_group_target(text: str, card_name: str) -> dict[str, Any]:
    normalized = strip_reminder_text(normalize_whitespace(text)).lower().rstrip(".")
    normalized = normalized.replace(card_name.lower(), "self")
    normalized = normalized.replace("this creature", "self")

    match = re.fullmatch(r"each ([a-z' -]+) you control", normalized)
    if match:
        descriptor = match.group(1).strip()
        words = [word for word in descriptor.split() if word and word not in ARTICLE_WORDS]

        if words:
            return build_group_target(words)

    match = re.fullmatch(r"another ([a-z' -]+) you control", normalized)
    if match:
        descriptor = match.group(1).strip()
        words = [word for word in descriptor.split() if word and word not in ARTICLE_WORDS]

        if words:
            return build_group_target(words, exclude_self=True)

    match = re.fullmatch(r"other ([a-z' -]+) you control", normalized)
    if match:
        descriptor = match.group(1).strip()
        words = [word for word in descriptor.split() if word and word not in ARTICLE_WORDS]

        if words:
            return build_group_target(words, exclude_self=True)

    match = re.fullmatch(r"([a-z' -]+) you control", normalized)
    if match:
        descriptor = match.group(1).strip()
        words = [word for word in descriptor.split() if word and word not in ARTICLE_WORDS]

        if words:
            return build_group_target(words)

    return {"selector": normalize_subject(text, card_name)}


def build_group_target(words: list[str], exclude_self: bool = False) -> dict[str, Any]:
    card_types = [_normalize_card_type_word(word) for word in words if word in CARD_TYPE_WORDS]
    subtypes = [_normalize_subtype_word(word) for word in words if word not in CARD_TYPE_WORDS]

    selector = "creatures_you_control"
    if card_types and not subtypes and card_types != ["Creature"]:
        selector = "permanents_you_control"
    if card_types == ["Creature"] and not subtypes:
        card_types = []

    target: dict[str, Any] = {"selector": selector}
    if exclude_self:
        target["exclude_self"] = True
    if card_types:
        target["card_types"] = card_types
    if subtypes:
        target["subtypes"] = subtypes
    return target


def _normalize_subtype_word(word: str) -> str:
    lowered = word.lower()
    if lowered == "faeries":
        return "Faerie"
    if lowered.endswith("ies") and len(lowered) > 3:
        return lowered[:-3].capitalize() + "y"
    if lowered.endswith("s") and len(lowered) > 1:
        return lowered[:-1].capitalize()
    return lowered.capitalize()


def _normalize_card_type_word(word: str) -> str:
    lowered = word.lower()
    if lowered.endswith("ies") and len(lowered) > 3:
        lowered = lowered[:-3] + "y"
    elif lowered.endswith("s") and len(lowered) > 1:
        lowered = lowered[:-1]
    return lowered.capitalize()


def parse_card_filter_description(text: str) -> dict[str, Any]:
    normalized = normalize_whitespace(text).strip().rstrip(".")
    lowered = normalized.lower()
    lowered = re.sub(r"^(a|an|any number of)\s+", "", lowered)
    lowered = re.sub(r"\s+cards?$", "", lowered)

    filter_payload: dict[str, Any] = {}
    if "legendary" in lowered:
        filter_payload["supertypes"] = ["Legendary"]
        lowered = lowered.replace("legendary", "").strip()

    parts = [part.strip() for part in re.split(r",| or ", lowered) if part.strip()]
    type_words: list[str] = []
    subtype_words: list[str] = []
    excluded_types: list[str] = []

    for part in parts:
        if part.startswith("non"):
            base = part[3:]
            if base in CARD_TYPE_WORDS:
                excluded_types.append(_normalize_card_type_word(base))
                continue

        words = [word for word in part.split() if word]
        part_type_words = [word for word in words if word in CARD_TYPE_WORDS]
        part_subtype_words = [word for word in words if word not in CARD_TYPE_WORDS]

        type_words.extend(part_type_words)
        subtype_words.extend(part_subtype_words)

    if type_words:
        filter_payload["card_types"] = sorted({
            _normalize_card_type_word(word) for word in type_words
        })
    if subtype_words:
        filter_payload["subtypes_any"] = sorted({
            _normalize_subtype_word(word) for word in subtype_words
        })
    if excluded_types:
        filter_payload["not_card_types"] = sorted(set(excluded_types))

    if not filter_payload:
        filter_payload["text"] = normalized
    return filter_payload


def parse_subject_or_group(text: str, card_name: str) -> str | dict[str, Any]:
    if "you control" in text.lower():
        return parse_group_target(text, card_name)
    return normalize_subject(text, card_name)


def parse_condition_fragment(text: str, card_name: str) -> list[dict[str, Any]]:
    normalized = strip_reminder_text(normalize_whitespace(text)).rstrip(".")
    lowered = normalized.lower()

    if lowered == "you've cast both a creature spell and a noncreature spell this turn":
        return [
            {"event_this_turn": "cast_creature_spell", "count_gte": 1},
            {"event_this_turn": "cast_noncreature_spell", "count_gte": 1},
        ]

    match = re.fullmatch(r"there's a ([a-z' -]+) card in your graveyard", lowered)
    if match:
        return [{
            "zone_contains": "graveyard",
            "owner": "you",
            "card_descriptor": match.group(1).replace(" ", "_"),
            "count_gte": 1,
        }]

    match = re.fullmatch(r"that targets? a ([a-z' -]+) you control", lowered)
    if match:
        return [{
            "spell_targets": normalize_subject(match.group(1) + " you control", card_name),
        }]

    match = re.fullmatch(r"from ([a-z]+)", lowered)
    if match:
        return [{
            "from_zone": match.group(1),
        }]

    match = re.fullmatch(r"a player lost (\d+) or more life this turn", lowered)
    if match:
        return [{
            "event_this_turn": "life_lost",
            "subject": "any_player",
            "amount_gte": int(match.group(1)),
        }]

    match = re.fullmatch(r"(\w+) or more creatures died this turn", lowered)
    if match:
        amount = parse_number(match.group(1))
        return [{
            "event_this_turn": "creature_died",
            "count_gte": amount or match.group(1),
        }]

    match = re.fullmatch(r"during your turn and only once each turn", lowered)
    if match:
        return [
            {"turn_scope": "your_turn"},
            {"max_uses_per_turn": 1},
        ]

    match = re.fullmatch(r"(.+?) is in the command zone or on the battlefield", lowered)
    if match:
        return [{
            "subject": normalize_subject(match.group(1), card_name),
            "zones_any": ["command_zone", "battlefield"],
        }]

    if lowered == "you have no cards in hand":
        return [{
            "zone_count": {
                "zone": "hand",
                "owner": "you",
                "count_eq": 0,
            }
        }]

    if lowered == "this is the second time this ability has resolved this turn":
        return [{
            "ability_resolution_count_this_turn": 2,
        }]

    match = re.fullmatch(r"this is the (\w+) time this ability has resolved this turn", lowered)
    if match:
        amount = parse_number(match.group(1))
        return [{
            "ability_resolution_count_this_turn": amount or match.group(1),
        }]

    match = re.fullmatch(rf"{re.escape(card_name.lower())} has power (\d+) or greater", lowered)
    if match:
        return [{
            "subject": "self",
            "attribute": "power",
            "operator": "gte",
            "value": int(match.group(1)),
        }]

    primary_name = card_name.split("//", 1)[0].split(",", 1)[0].strip().lower()
    if primary_name:
        match = re.fullmatch(rf"{re.escape(primary_name)} has power (\d+) or greater", lowered)
        if match:
            return [{
                "subject": "self",
                "attribute": "power",
                "operator": "gte",
                "value": int(match.group(1)),
            }]

    return [{"condition_text": normalized}]


def parse_trigger_header(header: str, card_name: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    header = strip_reminder_text(normalize_whitespace(header)).rstrip(",")
    lowered = header.lower()

    if lowered == "at the beginning of combat on your turn":
        return {"type": "beginning_of_combat_your_turn"}, []

    if lowered == "at the beginning of each player's upkeep":
        return {"type": "beginning_of_each_players_upkeep"}, []

    if lowered == "at the beginning of each opponent's upkeep":
        return {"type": "beginning_of_each_opponents_upkeep"}, []

    if lowered == "at the beginning of the end step":
        return {"type": "beginning_of_end_step"}, []

    if lowered == "at end of combat":
        return {"type": "end_of_combat"}, []

    if lowered == "at the beginning of each player's end step":
        return {"type": "beginning_of_each_players_end_step"}, []

    if lowered == "at the beginning of each player's draw step":
        return {"type": "beginning_of_each_players_draw_step"}, []

    if lowered == "at the beginning of the upkeep of enchanted creature's controller":
        return {"type": "beginning_of_upkeep_of_enchanted_creatures_controller"}, []

    match = re.fullmatch(r"at the beginning of your ([a-z ]+)", lowered)
    if match:
        step = match.group(1).replace(" ", "_")
        return {"type": f"beginning_of_your_{step}"}, []

    match = re.fullmatch(r"at the beginning of each ([a-z ]+)", lowered)
    if match:
        step = match.group(1).replace(" ", "_")
        return {"type": f"beginning_of_each_{step}"}, []

    if lowered == "at the beginning of the next end step":
        return {"type": "beginning_of_next_end_step"}, []

    if lowered == "when you cast this spell":
        return {"type": "cast_this_spell", "subject": "you"}, []

    match = re.fullmatch(r"(when|whenever) (.+)", lowered)
    if match:
        body = match.group(2)

        if body == "you sacrifice a permanent":
            return {"type": "sacrifice_permanent", "subject": "you"}, []

        if body == "you play a card from exile":
            return {"type": "play_card", "subject": "you"}, [{"from_zone": "exile"}]

        if body == "you attack":
            return {"type": "attack_declared", "subject": "you"}, []

        if body == "you gain life":
            return {"type": "gain_life", "subject": "you"}, []

        if body == "you draw your second card each turn":
            return {"type": "draw_card", "subject": "you"}, [{"draw_count_each_turn": 2}]

        if body == "an opponent casts their second spell each turn":
            return {"type": "cast_spell", "subject": "an_opponent"}, [{"spell_cast_count_each_turn": 2}]

        if body == "you attack a player with one or more equipped creatures":
            return {"type": "attack_player_with_equipped_creatures", "subject": "you"}, []

        if body == "one or more creatures you control become the target of an activated ability":
            return {"type": "becomes_target_of_activated_ability", "subject": {"selector": "creatures_you_control"}}, []

        if body == "you draw a card":
            return {"type": "draw_card", "subject": "you"}, []

        if body == "an opponent casts a spell":
            return {"type": "cast_spell", "subject": "an_opponent"}, []

        if body == "a player casts a spell":
            return {"type": "cast_spell", "subject": "any_player"}, []

        if body == "an opponent draws a card":
            return {"type": "draw_card", "subject": "an_opponent"}, []

        if body == "an opponent discards a card":
            return {"type": "discard_card", "subject": "an_opponent"}, []

        if body == "you discard a card":
            return {"type": "discard_card", "subject": "you"}, []

        if body == "you cycle this card":
            return {"type": "cycle_this_card", "subject": "you"}, []

        if body == "you cycle or discard a card":
            return {"type": "cycle_or_discard_card", "subject": "you"}, []

        if body == "you scry":
            return {"type": "scry", "subject": "you"}, []

        if body == "you commit a crime":
            return {"type": "commit_crime", "subject": "you"}, []

        if body == "you sacrifice a clue":
            return {"type": "sacrifice_clue", "subject": "you"}, []

        if body == "one or more cards leave your graveyard":
            return {"type": "cards_leave_graveyard", "subject": "your_graveyard"}, []

        if body == "a creature attacks you or a planeswalker you control":
            return {"type": "attacks_you_or_your_planeswalker", "subject": "a_creature"}, []

        match_cast = re.fullmatch(
            r"you cast (?:an? )?(.+?) spell(?: with mana value (\d+) or greater)?(?: that (.+))?",
            body,
        )
        if match_cast:
            spell_descriptor = match_cast.group(1).strip()
            mana_value = match_cast.group(2)
            extra = match_cast.group(3)
            conditions: list[dict[str, Any]] = []

            if mana_value is not None:
                conditions.append({
                    "mana_value_gte": int(mana_value),
                })

            if spell_descriptor not in {"spell", "", "a", "an"}:
                another_match = re.fullmatch(r"another (.+)", spell_descriptor)
                if another_match:
                    spell_descriptor = another_match.group(1).strip()
                    conditions.append({"exclude_source_card": True})
                if " or " in spell_descriptor:
                    spell_types = [part.strip().replace(" ", "_") for part in spell_descriptor.split(" or ")]
                    conditions.append({"spell_types_any": spell_types})
                elif spell_descriptor in {word for word in CARD_TYPE_WORDS}:
                    conditions.append({"spell_types_any": [_normalize_card_type_word(spell_descriptor)]})
                elif spell_descriptor == "noncreature":
                    conditions.append({"spell_types_excluded": ["Creature"]})
                else:
                    words = [word for word in spell_descriptor.split() if word]
                    type_words = [word for word in words if word in CARD_TYPE_WORDS]
                    subtype_words = [word for word in words if word not in CARD_TYPE_WORDS]

                    if type_words:
                        conditions.append({
                            "spell_types_any": [_normalize_card_type_word(word) for word in type_words],
                        })
                    if subtype_words:
                        conditions.append({
                            "spell_subtypes_all": [_normalize_subtype_word(word) for word in subtype_words],
                        })

            if extra:
                conditions.extend(parse_condition_fragment(f"that {extra}", card_name))

            return {"type": "cast_spell", "subject": "you"}, conditions

        multi_type_cast_match = re.fullmatch(r"you cast an? ([a-z]+), ([a-z]+), or ([a-z]+) spell", body)
        if multi_type_cast_match:
            return {
                "type": "cast_spell",
                "subject": "you",
            }, [{
                "spell_types_any": [
                    _normalize_card_type_word(multi_type_cast_match.group(1)),
                    _normalize_card_type_word(multi_type_cast_match.group(2)),
                    _normalize_card_type_word(multi_type_cast_match.group(3)),
                ]
            }]

        first_spell_match = re.fullmatch(r"you cast your first spell during each opponent's turn", body)
        if first_spell_match:
            return {
                "type": "cast_spell",
                "subject": "you",
            }, [
                {"turn_scope": "each_opponents_turn"},
                {"spell_cast_count_this_turn": 1},
            ]

        second_spell_match = re.fullmatch(r"you cast your second spell each turn", body)
        if second_spell_match:
            return {
                "type": "cast_spell",
                "subject": "you",
            }, [{"spell_cast_count_each_turn": 2}]

        play_or_cast_match = re.fullmatch(r"you play a land or cast a spell", body)
        if play_or_cast_match:
            return {
                "type": "play_land_or_cast_spell",
                "subject": "you",
            }, []

        if body.endswith(" enters or attacks"):
            subject = parse_subject_or_group(body[:-18], card_name)
            return {"type": "enters_or_attacks", "subject": subject}, []

        if body.endswith(" is turned face up"):
            subject = parse_subject_or_group(body[:-17], card_name)
            return {"type": "turned_face_up", "subject": subject}, []

        if body.endswith(" unlock this door"):
            subject = parse_subject_or_group(body[:-17], card_name)
            return {"type": "unlock_door", "subject": subject}, []

        if body.endswith(" mutates"):
            subject = parse_subject_or_group(body[:-8], card_name)
            return {"type": "mutates", "subject": subject}, []

        if body.endswith(" exploits a creature"):
            subject = parse_subject_or_group(body[:-19], card_name)
            return {"type": "exploits_creature", "subject": subject}, []

        if body.endswith(" becomes monstrous"):
            subject = parse_subject_or_group(body[:-18], card_name)
            return {"type": "becomes_monstrous", "subject": subject}, []

        if body.endswith(" becomes the target of a spell or ability"):
            subject = parse_subject_or_group(body[:-39], card_name)
            return {"type": "becomes_target_of_spell_or_ability", "subject": subject}, []

        match_attack_group = re.fullmatch(r"(.+?) and at least one other creature attack", body)
        if match_attack_group:
            subject = parse_subject_or_group(match_attack_group.group(1), card_name)
            return {
                "type": "attacks",
                "subject": subject,
            }, [{"attacking_creatures_you_control_gte": 2}]

        match_attack_group_three = re.fullmatch(r"(.+?) and at least two other creatures attack", body)
        if match_attack_group_three:
            subject = parse_subject_or_group(match_attack_group_three.group(1), card_name)
            return {
                "type": "attacks",
                "subject": subject,
            }, [{"attacking_creatures_you_control_gte": 3}]

        if body.endswith(" enters"):
            subject = parse_subject_or_group(body[:-7], card_name)
            return {"type": "enters_battlefield", "subject": subject}, []

        if body.endswith(" attacks alone"):
            subject = parse_subject_or_group(body[:-14], card_name)
            return {"type": "attacks_alone", "subject": subject}, []

        if body.endswith(" leaves the battlefield"):
            subject = parse_subject_or_group(body[:-23], card_name)
            return {"type": "leave_battlefield", "subject": subject}, []

        if body.endswith(" attacks an opponent"):
            subject = parse_subject_or_group(body[:-19], card_name)
            return {"type": "attacks_opponent", "subject": subject}, []

        first_time_attack_match = re.fullmatch(r"(.+?) attacks for the first time each turn", body)
        if first_time_attack_match:
            subject = parse_subject_or_group(first_time_attack_match.group(1), card_name)
            return {"type": "attacks", "subject": subject}, [{"attack_count_each_turn": 1}]

        if body.endswith(" attacks"):
            subject = parse_subject_or_group(body[:-8], card_name)
            return {"type": "attacks", "subject": subject}, []

        if body.endswith(" attacks or blocks"):
            subject = parse_subject_or_group(body[:-18], card_name)
            return {"type": "attacks_or_blocks", "subject": subject}, []

        if body.endswith(" attacks and isn't blocked"):
            subject = parse_subject_or_group(body[:-26], card_name)
            return {"type": "attacks_and_isnt_blocked", "subject": subject}, []

        if body.endswith(" attacks while saddled"):
            subject = parse_subject_or_group(body[:-21], card_name)
            return {"type": "attacks_while_saddled", "subject": subject}, []

        if body.endswith(" becomes blocked"):
            subject = parse_subject_or_group(body[:-16], card_name)
            return {"type": "becomes_blocked", "subject": subject}, []

        if body.endswith(" becomes blocked by a creature"):
            subject = parse_subject_or_group(body[:-30], card_name)
            return {"type": "becomes_blocked_by_creature", "subject": subject}, []

        if body.endswith(" blocks or becomes blocked by a creature"):
            subject = parse_subject_or_group(body[:-38], card_name)
            return {"type": "blocks_or_becomes_blocked_by_creature", "subject": subject}, []

        if body.endswith(" blocks a creature"):
            subject = parse_subject_or_group(body[:-18], card_name)
            return {"type": "blocks_creature", "subject": subject}, []

        if body.endswith(" blocks"):
            subject = parse_subject_or_group(body[:-7], card_name)
            return {"type": "blocks", "subject": subject}, []

        if body.endswith(" is dealt damage"):
            subject = parse_subject_or_group(body[:-15], card_name)
            return {"type": "dealt_damage", "subject": subject}, []

        counters_damage_match = re.fullmatch(
            r"one or more (.+?) with counters on them deal combat damage to a player",
            body,
        )
        if counters_damage_match:
            subject = parse_subject_or_group(counters_damage_match.group(1), card_name)
            return {
                "type": "deals_combat_damage_to_player",
                "subject": subject,
            }, [{"subject_has_counters": True}]

        grouped_damage_match = re.fullmatch(
            r"one or more (.+?) deal combat damage to a player",
            body,
        )
        if grouped_damage_match:
            subject = parse_subject_or_group(grouped_damage_match.group(1), card_name)
            return {
                "type": "deals_combat_damage_to_player",
                "subject": subject,
            }, []

        grouped_attack_match = re.fullmatch(
            r"one or more (.+?) attack",
            body,
        )
        if grouped_attack_match:
            subject = parse_subject_or_group(grouped_attack_match.group(1), card_name)
            return {
                "type": "attacks",
                "subject": subject,
            }, []

        if body.endswith(" deals combat damage to a player"):
            subject_text = body[:-31]
            counters_match = re.fullmatch(r"one or more (.+?) with counters on them", subject_text)
            if counters_match:
                subject = parse_subject_or_group(counters_match.group(1), card_name)
                conditions = [{"subject_has_counters": True}]
                return {"type": "deals_combat_damage_to_player", "subject": subject}, conditions

            subject = parse_subject_or_group(subject_text, card_name)
            return {"type": "deals_combat_damage_to_player", "subject": subject}, []

        if body.endswith(" deals combat damage to a creature"):
            subject = parse_subject_or_group(body[:-33], card_name)
            return {"type": "deals_combat_damage_to_creature", "subject": subject}, []

        if body.endswith(" deals damage to a player"):
            subject = parse_subject_or_group(body[:-25], card_name)
            return {"type": "deals_damage_to_player", "subject": subject}, []

        if body.endswith(" deals damage to an opponent"):
            subject = parse_subject_or_group(body[:-28], card_name)
            return {"type": "deals_damage_to_opponent", "subject": subject}, []

        if body.endswith(" deals damage"):
            subject = parse_subject_or_group(body[:-13], card_name)
            return {"type": "deals_damage", "subject": subject}, []

        if body.endswith(" dies"):
            subject = parse_subject_or_group(body[:-5], card_name)
            return {"type": "dies", "subject": subject}, []

        if body.endswith(" leave the battlefield without dying"):
            subject = parse_subject_or_group(body[:-35], card_name)
            return {
                "type": "leave_battlefield",
                "subject": subject,
                "without_dying": True,
            }, []

    return {"type": "custom", "text": header}, []


def split_sentences(text: str) -> list[str]:
    stripped = strip_reminder_text(text).strip()
    if not stripped:
        return []
    parts = re.split(r"(?<=\.)\s+", stripped)
    cleaned_parts: list[str] = []
    for part in parts:
        cleaned = part.strip().strip("()").rstrip(".").strip()
        if cleaned:
            cleaned_parts.append(cleaned)
    return cleaned_parts


def maybe_split_conjoined_actions(text: str) -> list[str]:
    candidates = [text]
    if " and " not in text.lower():
        return candidates

    parts = [part.strip() for part in re.split(r"\band\b", text, flags=re.IGNORECASE) if part.strip()]
    if len(parts) <= 1:
        return candidates

    recognized = 0
    for part in parts:
        if parse_effect_atom(part, ""):
            recognized += 1

    if recognized == len(parts):
        return parts
    return candidates


def parse_token_description(text: str) -> dict[str, Any]:
    token = {"raw": text}
    color_match = re.findall(r"\bwhite\b|\bblue\b|\bblack\b|\bred\b|\bgreen\b", text.lower())
    if color_match:
        token["colors"] = color_match
    pt_match = re.search(r"(\d+/\d+)", text)
    if pt_match:
        token["power_toughness"] = pt_match.group(1)
    if "creature token" in text.lower():
        token["card_types"] = ["creature"]
    subtype_match = re.search(r"\d+/\d+\s+([A-Za-z ]+?)\s+creature token", text)
    if subtype_match:
        token["subtypes"] = [
            part for part in subtype_match.group(1).split()
            if part and part.lower() not in COLOR_WORDS
        ]
    keyword_match = re.search(r"creature token with ([A-Za-z, ]+)", text)
    if keyword_match:
        token["keywords"] = [
            keyword.strip().replace(" ", "_")
            for keyword in re.split(r",| and ", keyword_match.group(1))
            if keyword.strip()
        ]
    if "treasure token" in text.lower():
        token["subtypes"] = ["Treasure"]
    return token


def parse_effect_atom(text: str, card_name: str) -> list[dict[str, Any]]:
    normalized = strip_reminder_text(normalize_whitespace(text)).rstrip('."').strip('"')
    lowered = normalized.lower()
    effects: list[dict[str, Any]] = []

    if not normalized:
        return effects

    if lowered in {
        "attach to target creature you control",
        "equip only as a sorcery",
        "this vehicle becomes an artifact creature until end of turn",
    }:
        return [{"action": "ignored_effect"}]

    activate_only_match = re.fullmatch(r"activate only if (.*)", lowered)
    if activate_only_match:
        return [{
            "action": "activation_restriction",
            "condition": parse_condition_fragment(activate_only_match.group(1), card_name),
        }]

    activate_only_compound_match = re.fullmatch(r"activate only (.*)", lowered)
    if activate_only_compound_match:
        return [{
            "action": "activation_restriction",
            "condition": parse_condition_fragment(activate_only_compound_match.group(1), card_name),
        }]

    once_each_turn_match = re.fullmatch(r"do this only once each turn", lowered)
    if once_each_turn_match:
        return [{
            "action": "usage_limit",
            "scope": "each_turn",
            "max_uses": 1,
        }]

    triggers_once_each_turn_match = re.fullmatch(r"this ability triggers only once each turn", lowered)
    if triggers_once_each_turn_match:
        return [{
            "action": "usage_limit",
            "scope": "each_turn",
            "max_triggers": 1,
        }]

    when_you_do_match = re.fullmatch(r"when you do, (.*)", lowered)
    if when_you_do_match:
        nested_effects = parse_effects_text(when_you_do_match.group(1), card_name)
        for effect in nested_effects:
            effect_conditions = list(effect.get("condition", []))
            effect["condition"] = effect_conditions + [{"previous_optional_payment_made": True}]
        return nested_effects

    conditional_prefix = re.fullmatch(r"then if (.*?), (.*)", lowered)
    if conditional_prefix:
        conditions = parse_condition_fragment(conditional_prefix.group(1), card_name)
        nested_effects = parse_effects_text(conditional_prefix.group(2), card_name)
        for effect in nested_effects:
            effect_conditions = list(effect.get("condition", []))
            effect["condition"] = effect_conditions + conditions
        return nested_effects

    if_you_do_match = re.fullmatch(r"if you do, (.*)", lowered)
    if if_you_do_match:
        nested_effects = parse_effects_text(if_you_do_match.group(1), card_name)
        for effect in nested_effects:
            effect_conditions = list(effect.get("condition", []))
            effect["condition"] = effect_conditions + [{"previous_optional_payment_made": True}]
        return nested_effects

    then_match = re.fullmatch(r"(.*), then (.*)", lowered)
    if then_match:
        first_effects = parse_effects_text(then_match.group(1), card_name)
        second_effects = parse_effects_text(then_match.group(2), card_name)
        if first_effects and second_effects:
            return first_effects + second_effects

    if_clause_match = re.fullmatch(r"if (.*?), (.*)", lowered)
    if if_clause_match:
        conditions = parse_condition_fragment(if_clause_match.group(1), card_name)
        nested_effects = parse_effects_text(if_clause_match.group(2), card_name)
        for effect in nested_effects:
            effect_conditions = list(effect.get("condition", []))
            effect["condition"] = effect_conditions + conditions
        return nested_effects

    draw_otherwise_discard_match = re.fullmatch(r"draw (a|an|\w+) cards? if (.*)", lowered)
    if draw_otherwise_discard_match:
        amount = parse_number(draw_otherwise_discard_match.group(1))
        conditions = parse_condition_fragment(draw_otherwise_discard_match.group(2), card_name)
        return [{
            "action": "draw_cards",
            "amount": amount or draw_otherwise_discard_match.group(1),
            "condition": conditions,
        }]

    otherwise_match = re.fullmatch(r"otherwise, (.*)", lowered)
    if otherwise_match:
        nested_effects = parse_effects_text(otherwise_match.group(1), card_name)
        for effect in nested_effects:
            effect_conditions = list(effect.get("condition", []))
            effect["condition"] = effect_conditions + [{
                "not": {
                    "zone_count": {
                        "zone": "hand",
                        "owner": "you",
                        "count_eq": 0,
                    }
                }
            }]
        return nested_effects

    optional = False
    if lowered.startswith("you may "):
        optional = True
        normalized = normalized[8:].strip()
        lowered = normalized.lower()

    if lowered == "add one mana of any color in your commander's color identity":
        effect = {
            "action": "add_mana",
            "amount": 1,
            "distribution": "commanders_color_identity",
        }
        if optional:
            effect["optional"] = True
        return [effect]

    if lowered == "add one mana of any color that a land an opponent controls could produce":
        effect = {
            "action": "add_mana",
            "amount": 1,
            "distribution": "opponents_land_producible_color",
        }
        if optional:
            effect["optional"] = True
        return [effect]

    if lowered in {"add {r}{r}, {r}{g}, or {g}{g}", "add {r}{r}, {r}{w}, or {w}{w}", "add {g}{w}", "add {r}{g}", "add {r}{w}", "add {r}, {g}, or {w}"}:
        symbols = re.findall(r"\{[^}]+\}", lowered)
        if len(symbols) == 2 and lowered.count("or") == 0 and lowered.count(",") == 0:
            return [{
                "action": "add_mana",
                "amount": 2,
                "colors_any_of": symbols,
                "distribution": "fixed_sequence",
            }]
        grouped = [group.strip() for group in lowered[4:].split(", or ")] if ", or " in lowered else [part.strip() for part in lowered[4:].split(", ")]
        choices = [re.findall(r"\{[^}]+\}", group) for group in grouped]
        return [{
            "action": "add_mana",
            "choices": choices,
            "distribution": "choose_one_group",
        }]

    pay_mana_match = re.fullmatch(r"pay (\{[^}]+\})", lowered)
    if pay_mana_match:
        return [{
            "action": "pay_mana",
            "cost": pay_mana_match.group(1),
            "optional": True,
        }]

    discard_match = re.fullmatch(r"discard (a|an|\w+) cards?", lowered)
    if discard_match:
        amount = parse_number(discard_match.group(1))
        effect = {
            "action": "discard_cards",
            "player": "you",
            "amount": amount or discard_match.group(1),
        }
        if optional:
            effect["optional"] = True
        return [effect]

    lose_life_draw_match = re.fullmatch(r"you draw (a|an|\w+) cards? and you lose (\d+) life", lowered)
    if lose_life_draw_match:
        amount = parse_number(lose_life_draw_match.group(1))
        effects = [{
            "action": "draw_cards",
            "amount": amount or lose_life_draw_match.group(1),
        }, {
            "action": "lose_life",
            "target": "you",
            "amount": int(lose_life_draw_match.group(2)),
        }]
        if optional:
            for effect in effects:
                effect["optional"] = True
        return effects

    additional_cost_sac_match = re.fullmatch(r"as an additional cost to cast this spell, sacrifice a creature", lowered)
    if additional_cost_sac_match:
        return [{
            "action": "additional_cost",
            "cost": {
                "action": "sacrifice",
                "target": "a_creature_you_control",
            },
        }]

    move_counter_match = re.fullmatch(
        r"move a counter from target creature you control onto a second target creature you control",
        lowered,
    )
    if move_counter_match:
        effect = {
            "action": "move_counter",
            "source": {
                "selector": "target_creature_you_control",
            },
            "destination": {
                "selector": "second_target_creature_you_control",
            },
            "counter_count": 1,
        }
        if optional:
            effect["optional"] = True
        return [effect]

    reveal_it_match = re.fullmatch(r"you may reveal it", lowered)
    if reveal_it_match:
        return [{"action": "reveal_card", "object": "it", "optional": True}]

    exact_effects: dict[str, list[dict[str, Any]]] = {
        "this land deals 1 damage to you": [{"action": "deal_damage", "source": "self", "target": "you", "amount": 1}],
        "this land enters tapped unless you control two or more basic lands": [{"action": "enters_tapped_unless", "target": "self", "condition": [{"you_control_basic_lands_gte": 2}]}],
        "this land enters tapped unless you control a mountain or a plains": [{"action": "enters_tapped_unless", "target": "self", "condition": [{"you_control_subtypes_any": ["Mountain", "Plains"]}]}],
        "this land enters tapped unless you control a mountain or a forest": [{"action": "enters_tapped_unless", "target": "self", "condition": [{"you_control_subtypes_any": ["Mountain", "Forest"]}]}],
        "this land enters tapped unless you control a forest or a plains": [{"action": "enters_tapped_unless", "target": "self", "condition": [{"you_control_subtypes_any": ["Forest", "Plains"]}]}],
        "as this land enters, you may reveal a forest or plains card from your hand": [{"action": "as_enters_optional_reveal", "target": "self", "from_zone": "hand", "filter": {"subtypes_any": ["Forest", "Plains"]}}],
        "as this land enters, you may reveal a mountain or plains card from your hand": [{"action": "as_enters_optional_reveal", "target": "self", "from_zone": "hand", "filter": {"subtypes_any": ["Mountain", "Plains"]}}],
        "as this land enters, you may reveal a mountain or forest card from your hand": [{"action": "as_enters_optional_reveal", "target": "self", "from_zone": "hand", "filter": {"subtypes_any": ["Mountain", "Forest"]}}],
        "equipped creature gets +2/+2 and has trample and lifelink": [{"action": "modify_stats", "target": "equipped_creature", "power_delta": 2, "toughness_delta": 2, "keywords": ["trample", "lifelink"]}],
        "equipped creature gets +10/+10 and loses flying": [{"action": "modify_stats", "target": "equipped_creature", "power_delta": 10, "toughness_delta": 10, "lose_keywords": ["flying"]}],
        "equipped creature has indestructible": [{"action": "grant_keyword", "target": "equipped_creature", "keyword": "indestructible"}],
        "equipped creature has double strike": [{"action": "grant_keyword", "target": "equipped_creature", "keyword": "double_strike"}],
        "equipped creature has nonbasic landwalk": [{"action": "grant_keyword", "target": "equipped_creature", "keyword": "nonbasic_landwalk"}],
        "equipped creature can't be blocked except by walls": [{"action": "combat_restriction", "target": "equipped_creature", "restriction": "cant_be_blocked_except_by", "except_by": "Wall"}],
        "equipped creature gets +1/+1 for each artifact you control": [{"action": "modify_stats", "target": "equipped_creature", "power_delta": {"kind": "count", "object": {"selector": "permanents_you_control", "card_types": ["Artifact"]}}, "toughness_delta": {"kind": "count", "object": {"selector": "permanents_you_control", "card_types": ["Artifact"]}}}],
        "equipped creature gets +1/+1 for each land you control": [{"action": "modify_stats", "target": "equipped_creature", "power_delta": {"kind": "count", "object": {"selector": "permanents_you_control", "card_types": ["Land"]}}, "toughness_delta": {"kind": "count", "object": {"selector": "permanents_you_control", "card_types": ["Land"]}}}],
        "equipped creature gets +1/+1 for each color among permanents you control": [{"action": "modify_stats", "target": "equipped_creature", "power_delta": {"kind": "count_colors_among", "object": {"selector": "permanents_you_control"}}, "toughness_delta": {"kind": "count_colors_among", "object": {"selector": "permanents_you_control"}}}],
        "equipped creature has base power and toughness x/x, where x is your life total": [{"action": "set_base_power_toughness", "target": "equipped_creature", "power": {"kind": "player_life_total", "player": "you"}, "toughness": {"kind": "player_life_total", "player": "you"}}],
        "equipped creature has base power and toughness 7/7 and can't be blocked by creatures with power 2 or less": [{"action": "set_base_power_toughness", "target": "equipped_creature", "power": 7, "toughness": 7, "combat_restriction": {"restriction": "cant_be_blocked_by_power_lte", "value": 2}}],
        "equipped creature gets +2/+2": [{"action": "modify_stats", "target": "equipped_creature", "power_delta": 2, "toughness_delta": 2}],
        "equipped creature gets +3/+2": [{"action": "modify_stats", "target": "equipped_creature", "power_delta": 3, "toughness_delta": 2}],
        "equipped creature gets +2/+1": [{"action": "modify_stats", "target": "equipped_creature", "power_delta": 2, "toughness_delta": 1}],
        "equipped creature gets +1/+1": [{"action": "modify_stats", "target": "equipped_creature", "power_delta": 1, "toughness_delta": 1}],
        "as long as equipped creature is legendary, it has hexproof": [{"action": "grant_keyword", "target": "equipped_creature", "keyword": "hexproof", "condition": [{"subject": "equipped_creature", "is_legendary": True}]}],
        "as long as equipped creature is legendary, it has trample and haste": [{"action": "grant_keywords", "target": "equipped_creature", "keywords": ["trample", "haste"], "condition": [{"subject": "equipped_creature", "is_legendary": True}]}],
        "as long as it's legendary, it gets an additional +2/+2": [{"action": "modify_stats", "target": "equipped_creature", "power_delta": 2, "toughness_delta": 2, "condition": [{"subject": "equipped_creature", "is_legendary": True}]}],
        "as long as it's red, it has trample": [{"action": "grant_keyword", "target": "equipped_creature", "keyword": "trample", "condition": [{"subject": "equipped_creature", "colors_include": ["red"]}]}],
        "your opponents can't cast spells during your turn": [{"action": "casting_restriction", "target": "your_opponents", "restriction": "cant_cast_spells", "condition": [{"turn_scope": "your_turn"}]}],
        "any number of target nonland permanents you control phase out": [{"action": "phase_out", "target": {"selector": "target_nonland_permanents_you_control"}, "target_count": "any"}],
        "put your commander into your hand from the command zone": [{"action": "move_card", "target": "your_commander", "source_zone": "command_zone", "destination_zone": "hand"}],
        "search your library for an aura or equipment card, reveal it, put it into your hand": [{"action": "search_library", "player": "you", "filter": {"card_types_any": ["Aura", "Equipment"]}, "reveal": True, "destination": "hand"}],
        "search your library for an aura card and/or an equipment card, reveal them, put them into your hand": [{"action": "search_library", "player": "you", "filter": {"card_types_any": ["Aura", "Equipment"]}, "reveal": True, "destination": "hand", "selected_count": {"min": 1, "max": 2}}],
        "search your library for an equipment card, reveal it, put it into your hand": [{"action": "search_library", "player": "you", "filter": {"card_types": ["Equipment"]}, "reveal": True, "destination": "hand"}],
        "search your library for an equipment card, put it onto the battlefield": [{"action": "search_library", "player": "you", "filter": {"card_types": ["Equipment"]}, "destination": "battlefield", "optional": True}],
        "search your library for up to two basic land cards, reveal those cards, put one onto the battlefield tapped and the other into your hand": [{"action": "search_library", "player": "you", "filter": {"card_types": ["Land"], "supertypes": ["Basic"]}, "selected_count": {"min": 0, "max": 2}, "distribution": [{"destination": "battlefield", "tapped": True, "count": 1}, {"destination": "hand", "count": 1}], "reveal": True}],
        "search your library for a basic land card, put that card onto the battlefield tapped": [{"action": "search_library", "player": "you", "filter": {"card_types": ["Land"], "supertypes": ["Basic"]}, "destination": "battlefield", "tapped": True}],
        "search your library for a forest card, put that card onto the battlefield": [{"action": "search_library", "player": "you", "filter": {"subtypes_any": ["Forest"]}, "destination": "battlefield"}],
        "return target equipment card from your graveyard to the battlefield": [{"action": "return_from_graveyard_to_battlefield", "player": "you", "target": {"card_types": ["Equipment"], "zone": "graveyard"}, "destination": "battlefield"}],
        "return target aura or equipment card from your graveyard to your hand": [{"action": "move_card", "target": {"selector": "target_card_in_your_graveyard", "card_types_any": ["Aura", "Equipment"]}, "destination_zone": "hand"}],
        "return up to two target aura and/or equipment cards from your graveyard to the battlefield attached to that creature": [{"action": "return_from_graveyard_to_battlefield_attached", "player": "you", "target": {"card_types_any": ["Aura", "Equipment"], "zone": "graveyard"}, "max_targets": 2, "attach_to": "that_creature"}],
        "put an aura or equipment card from among them onto the battlefield": [{"action": "move_selected_looked_at_cards", "optional": True, "selected_count": 1, "filter": {"card_types_any": ["Aura", "Equipment"]}, "destination": "battlefield"}],
        "attach it to a creature you control": [{"action": "attach_to_creature_you_control", "object": "it", "optional": True}],
        "attach up to one target equipment you control to target rebel you control": [{"action": "attach_equipment", "source": "target_equipment_you_control", "target": {"selector": "target_creature_you_control", "subtypes": ["Rebel"]}, "max_targets": 1}],
        "unattach an equipment from a creature you control": [{"action": "unattach_equipment", "source": {"selector": "equipment_attached_to_creature_you_control"}, "optional": True}],
        "tap that creature": [{"action": "tap", "target": "that_creature"}],
        "metalcraft — if you control three or more artifacts, exile that creature": [{"action": "exile", "target": "that_creature", "condition": [{"you_control_artifacts_gte": 3}]}],
        "once during each of your turns, you may cast an artifact spell from your graveyard": [{"action": "allow_cast_from_graveyard", "filter": {"card_types": ["Artifact"]}, "scope": "once_each_of_your_turns"}],
        "that artifact enters tapped": [{"action": "enters_tapped_modifier", "target": "that_artifact"}],
        "pay {0} rather than pay the equip cost of the first equip ability you activate each turn": [{"action": "equip_cost_override", "amount": 0, "scope": "first_equip_ability_each_turn", "optional": True}],
        "pay {0} rather than pay the equip cost of the first equip ability you activate during each of your turns": [{"action": "equip_cost_override", "amount": 0, "scope": "first_equip_ability_each_of_your_turns", "optional": True}],
        "during your turn, you may activate equip abilities any time you could cast an instant": [{"action": "grant_activation_timing_override", "ability_kind": "equip", "condition": [{"turn_scope": "your_turn"}], "as_though": "instant_speed"}],
        "other creatures you control get +1/+0 for each aura and equipment attached to kellan": [{"action": "modify_stats", "target": {"selector": "creatures_you_control", "exclude_self": True}, "power_delta": {"kind": "count_attached_aura_and_equipment", "object": "self"}, "toughness_delta": 0}],
        "the first legendary creature spell you cast each turn costs {2} less to cast": [{"action": "cost_reduction", "player": "you", "object": {"kind": "spells", "card_types": ["Creature"], "supertypes": ["Legendary"]}, "amount": 2, "scope": "first_each_turn"}],
        "legendary creatures you control get +2/+2": [{"action": "modify_stats", "target": {"selector": "creatures_you_control", "supertypes": ["Legendary"]}, "power_delta": 2, "toughness_delta": 2}],
        "spend this mana only to cast artifact spells or activate abilities of artifacts": [{"action": "mana_spend_restriction", "applies_to": "this_mana", "allowed_use": {"actions_any": [{"action": "cast_spell", "filter": {"card_types": ["Artifact"]}}, {"action": "activate_ability", "filter": {"source_card_types": ["Artifact"]}}]}}],
        "modular 1": [{"keyword": "modular", "amount": 1}],
        "other creatures you control get +2/+0 for each equipment attached to it": [{"action": "modify_stats", "target": {"selector": "creatures_you_control", "exclude_self": True}, "power_delta": {"kind": "count_attached_equipment_each_target"}, "toughness_delta": 0}],
        "you create a treasure token": [{"action": "create_token", "token": {"raw": "Treasure token", "subtypes": ["Treasure"]}}],
        "return target equipment card from your graveyard to the battlefield": [{"action": "return_from_graveyard_to_battlefield", "player": "you", "target": {"card_types": ["Equipment"], "zone": "graveyard"}, "destination": "battlefield"}],
        "nonartifact spells you cast have improvise": [{"action": "grant_keyword", "target": {"kind": "spells_you_cast", "not_card_types": ["Artifact"]}, "keyword": "improvise"}],
        "aura and equipment spells you cast cost {1} less to cast": [{"action": "cost_reduction", "player": "you", "object": {"kind": "spells", "card_types_any": ["Aura", "Equipment"]}, "amount": 1}],
        "return target aura or equipment card from your graveyard to your hand": [{"action": "move_card", "target": {"selector": "target_card_in_your_graveyard", "card_types_any": ["Aura", "Equipment"]}, "destination_zone": "hand"}],
        "you may exile up to one other target artifact or enchantment": [{"action": "exile", "target": {"selector": "target_permanent", "card_types_any": ["Artifact", "Enchantment"]}, "max_targets": 1, "optional": True}],
        "the first activated ability you activate during your turn that targets a creature you control costs {2} less to activate": [{"action": "activated_ability_cost_reduction", "amount": 2, "scope": "first_during_your_turn", "condition": [{"ability_targets_creature_you_control": True}]}],
        "put an equipment card from your hand or graveyard onto the battlefield": [{"action": "move_card", "player": "you", "filter": {"card_types": ["Equipment"]}, "source_zones_any": ["hand", "graveyard"], "destination_zone": "battlefield", "optional": True}],
        "attach an equipment you control to it": [{"action": "attach_equipment", "source": "equipment_you_control", "target": "it", "optional": True}],
        "enchanted creature loses all abilities and is a green elk creature with base power and toughness 3/3": [{"action": "set_characteristics", "target": "enchanted_creature", "remove_all_abilities": True, "colors": ["green"], "card_types": ["Creature"], "subtypes": ["Elk"], "base_power": 3, "base_toughness": 3}],
        "enchanted creature gets +2/+2, has first strike and vigilance, and is a legendary soldier in addition to its other types": [{"action": "modify_characteristics", "target": "enchanted_creature", "power_delta": 2, "toughness_delta": 2, "keywords": ["first_strike", "vigilance"], "add_supertypes": ["Legendary"], "add_subtypes": ["Soldier"]}],
        "look at the top card of your library any time": [{"action": "look_at_top_card_any_time", "player": "you"}],
        "as long as this equipment is attached to a creature, you may cast creature spells from the top of your library": [{"action": "allow_cast_from_top_of_library", "filter": {"card_types": ["Creature"]}, "condition": [{"subject": "self", "state": "attached_to_creature"}]}],
        "its controller gains life equal to its power": [{"action": "gain_life", "player": "its_controller", "amount": {"kind": "target_attribute", "target": "that_creature", "attribute": "power"}}],
        "there is an additional combat phase after this phase": [{"action": "add_combat_phase_after_this_phase"}],
        "after this phase, there is an additional combat phase": [{"action": "add_combat_phase_after_this_phase"}],
        "untap it and all samurai you control": [{"action": "untap", "target": ["it", {"selector": "creatures_you_control", "subtypes": ["Samurai"]}]}],
        "untap all creatures you control": [{"action": "untap", "target": {"selector": "creatures_you_control"}}],
        "melee": [{"keyword": "melee"}],
        "equipped creature has double strike": [{"action": "grant_keyword", "target": "equipped_creature", "keyword": "double_strike"}],
        "target creature can't be blocked this turn": [{"action": "combat_restriction_until_end_of_turn", "target": "target_creature", "restriction": "cant_be_blocked"}],
        "return target equipment card from your graveyard to the battlefield": [{"action": "return_from_graveyard_to_battlefield", "player": "you", "target": {"card_types": ["Equipment"], "zone": "graveyard"}, "destination": "battlefield"}],
        "return target nonland permanent to its owner's hand": [{"action": "move_card", "target": {"selector": "target_permanent", "not_card_types": ["Land"]}, "destination_zone": "hand", "owner": "its_owner"}],
        "exile target artifact or enchantment": [{"action": "exile", "target": {"selector": "target_permanent", "card_types_any": ["Artifact", "Enchantment"]}}],
        "equip legendary creature {3}": [{"action": "equip", "target": {"selector": "target_creature_you_control", "supertypes": ["Legendary"]}, "cost": "{3}", "timing": "sorcery_speed"}],
        "up to one target creature blocks it this combat if able": [{"action": "force_block_this_combat", "target": "up_to_one_target_creature", "object": "it", "optional_target": True}],
        "destroy target nonland permanent": [{"action": "destroy", "target": {"selector": "target_permanent", "not_card_types": ["Land"]}}],
        "its controller creates a 1/1 white human creature token": [{"action": "create_token", "target_player": "its_controller", "amount": 1, "token": {"raw": "1/1 white Human creature token", "colors": ["white"], "power_toughness": "1/1", "card_types": ["creature"], "subtypes": ["Human"]}}],
        "you may exile up to one other target artifact or enchantment": [{"action": "exile", "target": {"selector": "target_permanent", "card_types_any": ["Artifact", "Enchantment"]}, "max_targets": 1, "optional": True}],
        "when that mana is spent to cast a creature spell that shares a creature type with your commander, scry 1": [{"action": "mana_spend_trigger", "trigger": {"type": "cast_spell", "subject": "you"}, "condition": [{"spell_shares_creature_type_with_commander": True}], "effects": [{"action": "scry", "amount": 1}]}],
        "metalcraft — equipment you control have equip {0} as long as you control three or more artifacts": [{"action": "grant_equip_cost", "target": {"selector": "permanents_you_control", "card_types": ["Equipment"]}, "cost": "{0}", "condition": [{"you_control_artifacts_gte": 3}]}],
        "create a colorless equipment artifact token named stoneforged blade": [{"action": "create_token", "amount": 1, "token": {"raw": "Stoneforged Blade", "colors": [], "card_types": ["Artifact"], "subtypes": ["Equipment"], "name": "Stoneforged Blade"}}],
        "it has indestructible, \"equipped creature gets +5/+5 and has double strike,\" and equip {0}": [{"action": "grant_token_ability_bundle", "object": "last_created_token", "abilities": [{"action": "grant_keyword", "target": "equipped_creature", "keyword": "indestructible"}, {"action": "modify_stats", "target": "equipped_creature", "power_delta": 5, "toughness_delta": 5, "keywords": ["double_strike"]}, {"action": "equip", "target": {"selector": "target_creature_you_control"}, "cost": "{0}", "timing": "sorcery_speed"}]}],
        "nahiri, the lithomancer can be your commander": [{"action": "can_be_your_commander"}],
        "until your next turn, creatures can't attack you unless their controller pays {2} for each of those creatures": [{"action": "attack_tax", "target": "all_creatures", "defender": "you", "cost_per_attacker": "{2}", "duration": "until_your_next_turn"}],
        "exile target artifact, enchantment, or tapped creature an opponent controls": [{"action": "exile", "target": {"selector": "target_permanent", "any_of": [{"card_types": ["Artifact"]}, {"card_types": ["Enchantment"]}, {"card_types": ["Creature"], "state": "tapped", "controller": "an_opponent"}]}}],
        "attach any number of target equipment you control to it": [{"action": "attach_equipment", "source": {"selector": "target_equipment_you_control", "target_count": "any"}, "target": "it"}],
        "tiered": [{"action": "tiered"}],
        "destroy target artifact you don't control": [{"action": "destroy", "target": {"selector": "target_artifact", "controller_not": "you"}}],
        "overload {4}{r}": [{"action": "overload", "cost": "{4}{R}"}],
        "exile target nonland permanent an opponent controls until this artifact leaves the battlefield": [{"action": "exile_until_source_leaves_battlefield", "target": {"selector": "target_permanent", "not_card_types": ["Land"], "controller": "an_opponent"}, "source": "self"}],
        "create a token that's a copy of it, except it has \"this equipment's equip abilities cost {2} less to activate.\" sacrifice that token at the beginning of the next upkeep": [{"action": "create_token_copy", "object": "it", "modifications": [{"action": "equip_cost_reduction", "target": "self", "amount": 2}], "delayed_trigger": {"type": "beginning_of_next_upkeep", "effects": [{"action": "sacrifice", "target": "that_token"}]}}],
        "it gets +x/+0 until end of turn, where x is the greatest mana value among artifacts you control": [{"action": "modify_stats_until_end_of_turn", "target": "self", "power_delta": {"kind": "greatest_mana_value_among", "object": {"selector": "permanents_you_control", "card_types": ["Artifact"]}}, "toughness_delta": 0}],
        "put the rest of those cards on the bottom of your library in a random order": [{"action": "move_unselected_looked_at_cards", "destination": "bottom_of_library", "order": "random"}],
        "destroy all artifacts": [{"action": "destroy", "target": {"selector": "all_permanents", "card_types": ["Artifact"]}}],
        "destroy all enchantments": [{"action": "destroy", "target": {"selector": "all_permanents", "card_types": ["Enchantment"]}}],
        "destroy all creatures with mana value 3 or less": [{"action": "destroy", "target": {"selector": "all_creatures", "mana_value_lte": 3}}],
        "destroy all creatures with mana value 4 or greater": [{"action": "destroy", "target": {"selector": "all_creatures", "mana_value_gte": 4}}],
        "each creature you control gets +2/+0 for each equipment attached to it": [{"action": "modify_stats", "target": {"selector": "creatures_you_control"}, "power_delta": {"kind": "count_attached_equipment_each_target", "multiplier": 2}, "toughness_delta": 0}],
        "as long as this equipment is attached to a creature, your opponents can't cast spells during your turn": [{"action": "casting_restriction", "target": "your_opponents", "restriction": "cant_cast_spells", "condition": [{"subject": "self", "state": "attached_to_creature"}, {"turn_scope": "your_turn"}]}],
        "untap that land": [{"action": "untap", "target": "that_land"}],
        "equip abilities you activate cost {2} less to activate": [{"action": "equip_cost_reduction", "target": "you", "amount": 2}],
        "attach this equipment to it": [{"action": "attach_equipment", "source": "self", "target": "it", "optional": True}],
        "exile up to one other target artifact or enchantment": [{"action": "exile", "target": {"selector": "target_permanent", "card_types_any": ["Artifact", "Enchantment"], "exclude_previous_target": True}, "max_targets": 1, "optional": True}],
        "choose one": [{"action": "mode_selection", "choose_count": 1}],
        "choose both instead": [{"action": "mode_selection_modifier", "choose_count": 2, "condition": [{"you_control_commander": True}], "optional": True}],
        "level 2": [{"action": "class_level", "level": 2}],
        "level 3": [{"action": "class_level", "level": 3}],
        "• create a 1/1 white soldier creature token": [{"action": "create_token", "amount": 1, "token": {"raw": "1/1 white Soldier creature token", "colors": ["white"], "power_toughness": "1/1", "card_types": ["creature"], "subtypes": ["Soldier"]}}],
        "• put a +1/+1 counter on each of up to two soldiers you control": [{"action": "put_counters", "counter_type": "+1/+1", "target": {"selector": "creatures_you_control", "subtypes": ["Soldier"], "max_targets": 2, "optional_targets": True}, "amount": 1}],
        "• meteor strikes — {2} — double target creature's power and toughness until end of turn": [{"action": "double_power_toughness_until_end_of_turn", "target": "target_creature", "additional_cost": "{2}"}],
        "• final heaven — {6}{g} — triple target creature's power and toughness until end of turn": [{"action": "multiply_power_toughness_until_end_of_turn", "target": "target_creature", "multiplier": 3, "additional_cost": "{6}{G}"}],
    }
    if lowered in exact_effects:
        effects = exact_effects[lowered]
        if optional:
            for effect in effects:
                if "optional" not in effect:
                    effect["optional"] = True
        return effects

    connive_match = re.fullmatch(r"(.+?) connives", lowered)
    if connive_match:
        return [{
            "action": "connive",
            "target": parse_subject_or_group(connive_match.group(1), card_name),
            "amount": 1,
            "sequence": [
                {
                    "action": "draw_cards",
                    "amount": 1,
                },
                {
                    "action": "discard_cards",
                    "amount": 1,
                },
                {
                    "action": "put_counters",
                    "counter_type": "+1/+1",
                    "target": parse_subject_or_group(connive_match.group(1), card_name),
                    "amount": 1,
                    "condition": [
                        {
                            "discarded_card_matches": {
                                "not_card_types": ["land"],
                            }
                        }
                    ],
                },
            ],
        }]

    draw_match = re.fullmatch(r"draw (a|an|\w+) cards?", lowered)
    if draw_match:
        amount = parse_number(draw_match.group(1))
        effect: dict[str, Any] = {"action": "draw_cards", "amount": amount or draw_match.group(1)}
        if optional:
            effect["optional"] = True
        return [effect]

    regenerate_match = re.fullmatch(r"regenerate (this creature|it|self)", lowered)
    if regenerate_match:
        effect = {
            "action": "regenerate",
            "target": "self",
        }
        if optional:
            effect["optional"] = True
        return [effect]

    you_draw_match = re.fullmatch(r"you draw (a|an|\w+) cards?", lowered)
    if you_draw_match:
        amount = parse_number(you_draw_match.group(1))
        effect = {"action": "draw_cards", "amount": amount or you_draw_match.group(1)}
        if optional:
            effect["optional"] = True
        return [effect]

    target_opponent_draw_match = re.fullmatch(r"target opponent draws? (a|an|\w+) cards?", lowered)
    if target_opponent_draw_match:
        amount = parse_number(target_opponent_draw_match.group(1))
        effect = {
            "action": "draw_cards",
            "target": "target_opponent",
            "amount": amount or target_opponent_draw_match.group(1),
        }
        if optional:
            effect["optional"] = True
        return [effect]

    scry_match = re.fullmatch(r"scry (\d+)", lowered)
    if scry_match:
        return [{
            "action": "scry",
            "amount": int(scry_match.group(1)),
        }]

    surveil_match = re.fullmatch(r"surveil (\d+)", lowered)
    if surveil_match:
        return [{
            "action": "surveil",
            "amount": int(surveil_match.group(1)),
        }]

    draw_that_many_match = re.fullmatch(r"draw that many cards", lowered)
    if draw_that_many_match:
        effect = {
            "action": "draw_cards",
            "amount": "trigger_count",
            "count_source": "triggering_subject",
        }
        if optional:
            effect["optional"] = True
        return [effect]

    mill_match = re.fullmatch(r"mill (a|an|\w+) cards?", lowered)
    if mill_match:
        amount = parse_number(mill_match.group(1))
        effect = {
            "action": "mill_cards",
            "player": "you",
            "amount": amount or mill_match.group(1),
        }
        if optional:
            effect["optional"] = True
        return [effect]

    draw_for_each_match = re.fullmatch(r"draw (a|an|\w+) cards? for each (.+)", lowered)
    if draw_for_each_match:
        amount = parse_number(draw_for_each_match.group(1))
        effect = {
            "action": "draw_cards",
            "amount": "count",
            "count_multiplier": amount or draw_for_each_match.group(1),
            "count_object": normalize_subject(draw_for_each_match.group(2), card_name),
        }
        if optional:
            effect["optional"] = True
        return [effect]

    counter_match = re.fullmatch(
        r"put (a|an|\w+) \+1/\+1 counters? on (.+)",
        lowered,
    )
    if counter_match:
        amount = parse_number(counter_match.group(1))
        effect = {
            "action": "put_counters",
            "counter_type": "+1/+1",
            "target": parse_subject_or_group(counter_match.group(2), card_name),
            "amount": amount or counter_match.group(1),
        }
        if optional:
            effect["optional"] = True
        return [effect]

    enters_with_counters_match = re.fullmatch(
        r"this creature enters with (x|\d+|one|two|three|four|five|six|seven|eight|nine|ten|a|an) \+1/\+1 counters? on it",
        lowered,
    )
    if enters_with_counters_match:
        amount = parse_number(enters_with_counters_match.group(1))
        return [{
            "action": "enters_with_counters",
            "target": "self",
            "counter_type": "+1/+1",
            "amount": amount or enters_with_counters_match.group(1),
        }]

    gain_match = re.fullmatch(r"(.+?) gains? ([a-z ]+) until end of turn", lowered)
    if gain_match:
        target_text = gain_match.group(1).strip()
        target = "previous_target" if target_text == "it" else normalize_subject(target_text, card_name)
        effect = {
            "action": "grant_keyword_until_end_of_turn",
            "target": target,
            "keyword": gain_match.group(2).replace(" ", "_"),
        }
        if optional:
            effect["optional"] = True
        return [effect]

    gain_control_until_eot_match = re.fullmatch(r"gain control of target creature until end of turn", lowered)
    if gain_control_until_eot_match:
        return [{
            "action": "gain_control",
            "target": "target_creature",
            "duration": "until_end_of_turn",
        }]

    gains_keyword_match = re.fullmatch(r"(.+?) gains? ([a-z ]+)", lowered)
    if gains_keyword_match and gains_keyword_match.group(2).strip().replace(" ", "_") in {k.replace(" ", "_") for k in KEYWORDS}:
        target_text = gains_keyword_match.group(1).strip()
        target = "previous_target" if target_text == "it" else parse_subject_or_group(target_text, card_name)
        effect = {
            "action": "grant_keyword",
            "target": target,
            "keyword": gains_keyword_match.group(2).strip().replace(" ", "_"),
        }
        if optional:
            effect["optional"] = True
        return [effect]

    stat_change_until_eot_match = re.fullmatch(
        r"(.+?) gets ([+-]\d+)/([+-]\d+) until end of turn",
        lowered,
    )
    if stat_change_until_eot_match:
        target_text = stat_change_until_eot_match.group(1).strip()
        target = "previous_target" if target_text == "it" else parse_subject_or_group(target_text, card_name)
        effect = {
            "action": "modify_stats_until_end_of_turn",
            "target": target,
            "power_delta": int(stat_change_until_eot_match.group(2)),
            "toughness_delta": int(stat_change_until_eot_match.group(3)),
        }
        if optional:
            effect["optional"] = True
        return [effect]

    static_stat_bonus_match = re.fullmatch(
        r"(.+?) gets ([+-]\d+)/([+-]\d+)",
        lowered,
    )
    if static_stat_bonus_match:
        target = parse_subject_or_group(static_stat_bonus_match.group(1), card_name)
        return [{
            "action": "modify_stats",
            "target": target,
            "power_delta": int(static_stat_bonus_match.group(2)),
            "toughness_delta": int(static_stat_bonus_match.group(3)),
        }]

    static_keyword_match = re.fullmatch(
        r"during your turn, as long as (.+?) is equipped, it has ([a-z ,]+)",
        lowered,
    )
    if static_keyword_match:
        keywords = [
            keyword.strip().replace(" ", "_")
            for keyword in re.split(r",| and ", static_keyword_match.group(2))
            if keyword.strip()
        ]
        return [{
            "action": "grant_keywords",
            "target": "self",
            "keywords": keywords,
            "condition": [
                {"turn_scope": "your_turn"},
                {"subject": normalize_subject(static_keyword_match.group(1), card_name), "state": "equipped"},
            ],
        }]

    group_keyword_match = re.fullmatch(
        r"(.+?) have ([a-z ,]+)",
        lowered,
    )
    if group_keyword_match:
        keywords = [
            keyword.strip().replace(" ", "_")
            for keyword in re.split(r",| and ", group_keyword_match.group(2))
            if keyword.strip()
        ]
        if keywords and all(keyword in {k.replace(" ", "_") for k in KEYWORDS} for keyword in keywords):
            return [{
                "action": "grant_keywords",
                "target": parse_group_target(group_keyword_match.group(1), card_name),
                "keywords": keywords,
            }]

    stat_buff_match = re.fullmatch(
        r"(.+?) with ([a-z ]+) get ([+-]\d+)/([+-]\d+)",
        lowered,
    )
    if stat_buff_match:
        keyword_filter = stat_buff_match.group(2).strip().replace(" ", "_")
        return [{
            "action": "modify_stats",
            "target": {
                **parse_group_target(stat_buff_match.group(1), card_name),
                "keywords": [keyword_filter],
            },
            "power_delta": int(stat_buff_match.group(3)),
            "toughness_delta": int(stat_buff_match.group(4)),
        }]

    enters_with_counters_match = re.fullmatch(
        r"each other ([a-z' -]+) you control enters with an additional \+1/\+1 counter on it for each ([a-z' -]+) you already control",
        lowered,
    )
    if enters_with_counters_match:
        enters_words = [word for word in enters_with_counters_match.group(1).split() if word and word not in ARTICLE_WORDS]
        count_words = [word for word in enters_with_counters_match.group(2).split() if word and word not in ARTICLE_WORDS]
        return [{
            "action": "enters_with_additional_counters",
            "target": build_group_target(enters_words, exclude_self=True),
            "counter_type": "+1/+1",
            "amount": {
                "kind": "count",
                "object": build_group_target(count_words),
            },
        }]

    damage_each_opponent_match = re.fullmatch(r"(.+?) deals (\d+) damage to each opponent", lowered)
    if damage_each_opponent_match:
        effect = {
            "action": "deal_damage",
            "source": normalize_subject(damage_each_opponent_match.group(1), card_name),
            "target": "each_opponent",
            "amount": int(damage_each_opponent_match.group(2)),
        }
        if optional:
            effect["optional"] = True
        return [effect]

    damage_any_target_match = re.fullmatch(r"(.+?) deals (\d+) damage to any target", lowered)
    if damage_any_target_match:
        effect = {
            "action": "deal_damage",
            "source": parse_subject_or_group(damage_any_target_match.group(1), card_name),
            "target": "any_target",
            "amount": int(damage_any_target_match.group(2)),
        }
        if optional:
            effect["optional"] = True
        return [effect]

    lose_life_match = re.fullmatch(r"each opponent loses (\d+) life", lowered)
    if lose_life_match:
        effect = {
            "action": "lose_life",
            "target": "each_opponent",
            "amount": int(lose_life_match.group(1)),
        }
        if optional:
            effect["optional"] = True
        return [effect]

    reveal_hand_match = re.fullmatch(r"target opponent reveals their hand", lowered)
    if reveal_hand_match:
        return [{
            "action": "reveal_hand",
            "target": "target_opponent",
        }]

    discard_revealed_match = re.fullmatch(r"that player discards that card", lowered)
    if discard_revealed_match:
        return [{
            "action": "discard_revealed_card",
            "target": "that_player",
        }]

    target_lose_life_match = re.fullmatch(r"target opponent loses (\d+) life", lowered)
    if target_lose_life_match:
        effect = {
            "action": "lose_life",
            "target": "target_opponent",
            "amount": int(target_lose_life_match.group(1)),
        }
        if optional:
            effect["optional"] = True
        return [effect]

    target_player_reveals_hand_match = re.fullmatch(r"target player reveals their hand", lowered)
    if target_player_reveals_hand_match:
        return [{"action": "reveal_hand", "target": "target_player"}]

    gain_life_match = re.fullmatch(r"you gain (\d+) life", lowered)
    if gain_life_match:
        effect = {
            "action": "gain_life",
            "player": "you",
            "amount": int(gain_life_match.group(1)),
        }
        if optional:
            effect["optional"] = True
        return [effect]

    transform_match = re.fullmatch(r"transform (.+)", lowered)
    if transform_match:
        effect = {
            "action": "transform",
            "target": parse_subject_or_group(transform_match.group(1), card_name),
        }
        if optional:
            effect["optional"] = True
        return [effect]

    goad_match = re.fullmatch(r"goad target creature that player controls", lowered)
    if goad_match:
        effect = {
            "action": "goad",
            "target": "target_creature_controlled_by_damaged_player",
        }
        if optional:
            effect["optional"] = True
        return [effect]

    next_spell_copy_match = re.fullmatch(
        r"when you next cast an instant or sorcery spell this turn, copy (?:it|that spell)",
        lowered,
    )
    if next_spell_copy_match:
        effect = {
            "action": "create_delayed_trigger",
            "trigger": {
                "type": "cast_spell",
                "subject": "you",
            },
            "condition": [
                {"spell_types_any": ["instant", "sorcery"]},
                {"timing": "next_time_this_turn"},
            ],
            "effects": [
                {
                    "action": "copy_spell",
                    "object": "triggering_spell",
                }
            ],
        }
        if optional:
            effect["optional"] = True
        return [effect]

    choose_new_targets_match = re.fullmatch(r"(?:you may )?choose new targets for the copy", lowered)
    if choose_new_targets_match:
        effect = {
            "action": "allow_new_targets",
            "object": "copied_spell",
            "optional": True,
        }
        return [effect]

    equip_cost_reduction_match = re.fullmatch(
        r"equip abilities you activate that target (.+?) cost (\{[^}]+\}) less to activate",
        lowered,
    )
    if equip_cost_reduction_match:
        amount = parse_number(equip_cost_reduction_match.group(2))
        return [{
            "action": "equip_cost_reduction",
            "target": normalize_subject(equip_cost_reduction_match.group(1), card_name),
            "amount": amount or equip_cost_reduction_match.group(2),
        }]

    sacrifice_match = re.fullmatch(r"sacrifice (.+)", lowered)
    if sacrifice_match:
        effect = {
            "action": "sacrifice",
            "target": normalize_subject(sacrifice_match.group(1), card_name),
        }
        if optional:
            effect["optional"] = True
        return [effect]

    discard_your_hand_match = re.fullmatch(r"discard your hand", lowered)
    if discard_your_hand_match:
        return [{"action": "discard_hand", "player": "you"}]

    each_opponent_discards_match = re.fullmatch(r"each opponent discards (a|an|\w+) cards?", lowered)
    if each_opponent_discards_match:
        amount = parse_number(each_opponent_discards_match.group(1))
        return [{
            "action": "discard_cards",
            "target": "each_opponent",
            "amount": amount or each_opponent_discards_match.group(1),
        }]

    target_player_discards_match = re.fullmatch(r"target player discards (a|an|\w+) cards?", lowered)
    if target_player_discards_match:
        amount = parse_number(target_player_discards_match.group(1))
        return [{
            "action": "discard_cards",
            "target": "target_player",
            "amount": amount or target_player_discards_match.group(1),
        }]

    that_player_discards_match = re.fullmatch(r"that player discards (a|an|\w+) cards?", lowered)
    if that_player_discards_match:
        amount = parse_number(that_player_discards_match.group(1))
        return [{
            "action": "discard_cards",
            "target": "that_player",
            "amount": amount or that_player_discards_match.group(1),
        }]

    exile_target_creature_match = re.fullmatch(r"exile target creature", lowered)
    if exile_target_creature_match:
        return [{"action": "exile", "target": {"selector": "target_creature"}}]

    exile_target_nonland_perm_match = re.fullmatch(r"exile target nonland permanent", lowered)
    if exile_target_nonland_perm_match:
        return [{
            "action": "exile",
            "target": {"selector": "target_permanent", "not_card_types": ["Land"]},
        }]

    exile_target_graveyard_card_match = re.fullmatch(r"exile target card from a graveyard", lowered)
    if exile_target_graveyard_card_match:
        return [{
            "action": "exile",
            "target": {"selector": "target_card_in_graveyard"},
        }]

    destroy_target_match = re.fullmatch(r"destroy target creature", lowered)
    if destroy_target_match:
        return [{
            "action": "destroy",
            "target": {"selector": "target_creature"},
        }]

    destroy_target_land_match = re.fullmatch(r"destroy target land", lowered)
    if destroy_target_land_match:
        return [{
            "action": "destroy",
            "target": {"selector": "target_land"},
        }]

    destroy_target_artifact_or_enchantment_match = re.fullmatch(r"destroy target artifact or enchantment", lowered)
    if destroy_target_artifact_or_enchantment_match:
        return [{
            "action": "destroy",
            "target": {
                "selector": "target_permanent",
                "card_types_any": ["Artifact", "Enchantment"],
            },
        }]

    destroy_target_artifact_match = re.fullmatch(r"destroy target artifact", lowered)
    if destroy_target_artifact_match:
        return [{"action": "destroy", "target": {"selector": "target_artifact"}}]

    destroy_target_enchantment_match = re.fullmatch(r"destroy target enchantment", lowered)
    if destroy_target_enchantment_match:
        return [{"action": "destroy", "target": {"selector": "target_enchantment"}}]

    destroy_target_nonblack_creature_match = re.fullmatch(r"destroy target nonblack creature", lowered)
    if destroy_target_nonblack_creature_match:
        return [{
            "action": "destroy",
            "target": {"selector": "target_creature", "not_colors": ["black"]},
        }]

    destroy_target_tapped_creature_match = re.fullmatch(r"destroy target tapped creature", lowered)
    if destroy_target_tapped_creature_match:
        return [{
            "action": "destroy",
            "target": {"selector": "target_creature", "state": "tapped"},
        }]

    destroy_target_creature_or_planeswalker_match = re.fullmatch(r"destroy target creature or planeswalker", lowered)
    if destroy_target_creature_or_planeswalker_match:
        return [{
            "action": "destroy",
            "target": {"selector": "target_permanent", "card_types_any": ["Creature", "Planeswalker"]},
        }]

    destroy_all_creatures_match = re.fullmatch(r"destroy all creatures", lowered)
    if destroy_all_creatures_match:
        return [{"action": "destroy", "target": {"selector": "all_creatures"}}]

    destroy_that_creature_match = re.fullmatch(r"destroy that creature", lowered)
    if destroy_that_creature_match:
        return [{"action": "destroy", "target": "that_creature"}]

    destroy_it_match = re.fullmatch(r"destroy it", lowered)
    if destroy_it_match:
        return [{"action": "destroy", "target": "it"}]

    counter_target_spell_match = re.fullmatch(r"counter target spell", lowered)
    if counter_target_spell_match:
        return [{
            "action": "counter_spell",
            "target": "target_spell",
        }]

    counter_target_creature_spell_match = re.fullmatch(r"counter target creature spell", lowered)
    if counter_target_creature_spell_match:
        return [{
            "action": "counter_spell",
            "target": "target_creature_spell",
        }]

    tap_target_creature_match = re.fullmatch(r"tap target creature", lowered)
    if tap_target_creature_match:
        return [{
            "action": "tap",
            "target": "target_creature",
        }]

    untap_that_creature_match = re.fullmatch(r"untap that creature", lowered)
    if untap_that_creature_match:
        return [{
            "action": "untap",
            "target": "that_creature",
        }]

    untap_it_match = re.fullmatch(r"untap it", lowered)
    if untap_it_match:
        return [{"action": "untap", "target": "it"}]

    untap_self_match = re.fullmatch(r"untap this creature", lowered)
    if untap_self_match:
        return [{"action": "untap", "target": "self"}]

    tap_it_match = re.fullmatch(r"tap it", lowered)
    if tap_it_match:
        return [{"action": "tap", "target": "it"}]

    tap_enchanted_creature_match = re.fullmatch(r"tap enchanted creature", lowered)
    if tap_enchanted_creature_match:
        return [{"action": "tap", "target": "enchanted_creature"}]

    tap_target_opponent_creature_match = re.fullmatch(r"tap target creature an opponent controls", lowered)
    if tap_target_opponent_creature_match:
        return [{"action": "tap", "target": "target_creature_an_opponent_controls"}]

    tap_up_to_two_creatures_match = re.fullmatch(r"tap up to two target creatures", lowered)
    if tap_up_to_two_creatures_match:
        return [{
            "action": "tap",
            "target": "target_creatures",
            "max_targets": 2,
            "optional_targets": True,
        }]

    untap_target_creature_match = re.fullmatch(r"untap target creature", lowered)
    if untap_target_creature_match:
        return [{"action": "untap", "target": "target_creature"}]

    enchant_match = re.fullmatch(r"enchant (.+)", lowered)
    if enchant_match:
        descriptor = enchant_match.group(1).strip()
        return [{
            "action": "enchant_restriction",
            "target": {
                "selector": descriptor.replace(" ", "_"),
            },
        }]

    create_match = re.fullmatch(
        r"create (.+ token(?:s)?(?: with .+)?(?:, where .+)?)",
        normalized,
        re.IGNORECASE,
    )
    if create_match:
        token_text = create_match.group(1)
        where_x_match = re.fullmatch(
            r"x (.+ token(?:s)?(?: with .+)?), where x is the number of (.+)",
            token_text,
            re.IGNORECASE,
        )
        if where_x_match:
            effect = {
                "action": "create_token",
                "amount": "count",
                "count_object": parse_subject_or_group(where_x_match.group(2), card_name),
                "token": parse_token_description(where_x_match.group(1)),
            }
            if optional:
                effect["optional"] = True
            return [effect]
        amount_match = re.fullmatch(r"(a|an|\w+) (.+ token(?:s)?)", token_text, re.IGNORECASE)
        amount: int | str | None = 1
        if amount_match:
            amount = parse_number(amount_match.group(1)) or amount_match.group(1)
            token_text = amount_match.group(2)
        effect = {
            "action": "create_token",
            "amount": amount,
            "token": parse_token_description(token_text),
        }
        if optional:
            effect["optional"] = True
        return [effect]

    generic_tutor_match = re.fullmatch(
        r"search your library for a card, put it into your hand, then shuffle",
        lowered,
    )
    if generic_tutor_match:
        effect = {
            "action": "search_library",
            "player": "you",
            "filter": {"card_types": []},
            "destination": "hand",
            "shuffle": True,
        }
        if optional:
            effect["optional"] = True
        return [effect]

    shuffle_match = re.fullmatch(r"shuffle", lowered)
    if shuffle_match:
        effect = {
            "action": "shuffle_library",
            "player": "you",
        }
        if optional:
            effect["optional"] = True
        return [effect]

    add_mana_by_power_match = re.fullmatch(
        r"add x mana in any combination of (\{[^}]+\}) and/or (\{[^}]+\}), where x is (.+?)'s power",
        lowered,
    )
    if add_mana_by_power_match:
        effect = {
            "action": "add_mana",
            "amount": {
                "kind": "subject_attribute",
                "subject": normalize_subject(add_mana_by_power_match.group(3), card_name),
                "attribute": "power",
            },
            "colors_any_of": [
                add_mana_by_power_match.group(1),
                add_mana_by_power_match.group(2),
            ],
            "distribution": "any_combination",
        }
        if optional:
            effect["optional"] = True
        return [effect]

    add_double_colorless_match = re.fullmatch(r"add (\{[^}]+\}\{[^}]+\})", lowered)
    if add_double_colorless_match:
        symbols = re.findall(r"\{[^}]+\}", add_double_colorless_match.group(1))
        return [{
            "action": "add_mana",
            "amount": len(symbols),
            "colors_any_of": symbols,
            "distribution": "fixed_sequence",
        }]

    add_or_mana_match = re.fullmatch(r"add (\{[^}]+\}) or (\{[^}]+\})", lowered)
    if add_or_mana_match:
        return [{
            "action": "add_mana",
            "amount": 1,
            "colors_any_of": [add_or_mana_match.group(1), add_or_mana_match.group(2)],
            "distribution": "choose_one",
        }]

    add_fixed_mana_match = re.fullmatch(r"add (\{[^}]+\})", lowered)
    if add_fixed_mana_match:
        effect = {
            "action": "add_mana",
            "amount": 1,
            "colors_any_of": [add_fixed_mana_match.group(1)],
            "distribution": "fixed",
        }
        if optional:
            effect["optional"] = True
        return [effect]

    add_any_color_match = re.fullmatch(r"add one mana of any color", lowered)
    if add_any_color_match:
        effect = {
            "action": "add_mana",
            "amount": 1,
            "colors_any_of": ["{W}", "{U}", "{B}", "{R}", "{G}"],
            "distribution": "any_color",
        }
        if optional:
            effect["optional"] = True
        return [effect]

    add_two_any_one_color_match = re.fullmatch(r"add two mana of any one color", lowered)
    if add_two_any_one_color_match:
        return [{
            "action": "add_mana",
            "amount": 2,
            "colors_any_of": ["{W}", "{U}", "{B}", "{R}", "{G}"],
            "distribution": "same_color",
        }]

    spend_restriction_match = re.fullmatch(
        r"spend this mana only to cast an? ([a-z ]+) spell",
        lowered,
    )
    if spend_restriction_match:
        descriptor_words = [word for word in spend_restriction_match.group(1).split() if word]
        type_words = [word for word in descriptor_words if word in CARD_TYPE_WORDS]
        subtype_words = [word for word in descriptor_words if word not in CARD_TYPE_WORDS]

        filter_payload: dict[str, Any] = {"kind": "spells"}
        if type_words:
            filter_payload["card_types"] = [_normalize_card_type_word(word) for word in type_words]
        if subtype_words:
            filter_payload["subtypes_all"] = [_normalize_subtype_word(word) for word in subtype_words]

        effect = {
            "action": "mana_spend_restriction",
            "applies_to": "this_mana",
            "allowed_use": {
                "action": "cast_spell",
                "filter": filter_payload,
            },
        }
        if optional:
            effect["optional"] = True
        return [effect]

    equipment_tutor_match = re.fullmatch(
        r"search your library for an equipment card, reveal it, put it into your hand, then shuffle",
        lowered,
    )
    if equipment_tutor_match:
        effect = {
            "action": "search_library",
            "player": "you",
            "filter": {
                "card_types": ["Equipment"],
            },
            "reveal": True,
            "destination": "hand",
            "shuffle": True,
        }
        if optional:
            effect["optional"] = True
        return [effect]

    reanimate_match = re.fullmatch(
        r"return target creature card with power (\d+) or less from your graveyard to the battlefield tapped",
        lowered,
    )
    if reanimate_match:
        effect = {
            "action": "return_from_graveyard_to_battlefield",
            "player": "you",
            "target": {
                "card_types": ["creature"],
                "power_lte": int(reanimate_match.group(1)),
                "zone": "graveyard",
            },
            "destination": "battlefield",
            "tapped": True,
        }
        if optional:
            effect["optional"] = True
        return [effect]

    put_permanent_match = re.fullmatch(
        r"put a permanent card from your hand onto the battlefield",
        lowered,
    )
    if put_permanent_match:
        effect = {
            "action": "move_card",
            "player": "you",
            "source_zone": "hand",
            "destination_zone": "battlefield",
            "filter": {
                "card_types": ["Permanent"],
            },
        }
        if optional:
            effect["optional"] = True
        return [effect]

    put_attacking_match = re.fullmatch(
        r"put an? ([a-z ,]+) creature card from your hand onto the battlefield tapped and attacking that opponent",
        lowered,
    )
    if put_attacking_match:
        subtype_text = put_attacking_match.group(1)
        subtypes = [
            _normalize_subtype_word(part.strip())
            for part in re.split(r",| or ", subtype_text)
            if part.strip()
        ]
        effect = {
            "action": "move_card",
            "player": "you",
            "source_zone": "hand",
            "destination_zone": "battlefield",
            "filter": {
                "card_types": ["Creature"],
                "subtypes_any": subtypes,
            },
            "tapped": True,
            "attacking": "that_opponent",
        }
        if optional:
            effect["optional"] = True
        return [effect]

    attach_match = re.fullmatch(
        r"attach up to (a|an|\w+) target equipment you control to (it|self|this creature)",
        lowered,
    )
    if attach_match:
        amount = parse_number(attach_match.group(1))
        effect = {
            "action": "attach_equipment",
            "source": "target_equipment_you_control",
            "target": "self",
            "max_targets": amount or attach_match.group(1),
            "optional": True,
            "cheats_equip_cost": True,
        }
        return [effect]

    exile_top_match = re.fullmatch(r"exile the top card of your library", lowered)
    if exile_top_match:
        return [{
            "action": "move_top_card",
            "from_zone": "library",
            "to_zone": "exile",
            "owner": "you",
            "count": 1,
        }]

    play_until_match = re.fullmatch(r"until the end of your next turn, you may play that card", lowered)
    if play_until_match:
        return [{
            "action": "allow_play",
            "object": "that_card",
            "until": "end_of_your_next_turn",
        }]

    return_match = re.fullmatch(r"return it to your hand at the beginning of the next end step", lowered)
    if return_match:
        return [{
            "action": "delayed_return_to_hand",
            "object": "it",
            "trigger": "beginning_of_next_end_step",
        }]

    proliferate_match = re.fullmatch(r"proliferate", lowered)
    if proliferate_match:
        return [{"action": "proliferate"}]

    treasure_match = re.fullmatch(r"create a treasure token", lowered)
    if treasure_match:
        return [{
            "action": "create_token",
            "token": {"raw": "Treasure token", "subtypes": ["Treasure"]},
        }]

    investigate_match = re.fullmatch(r"investigate", lowered)
    if investigate_match:
        return [{
            "action": "investigate",
        }]

    monarch_match = re.fullmatch(r"you become the monarch", lowered)
    if monarch_match:
        return [{"action": "become_the_monarch"}]

    initiative_match = re.fullmatch(r"you take the initiative", lowered)
    if initiative_match:
        return [{"action": "take_the_initiative"}]

    ring_match = re.fullmatch(r"(?:the )?ring tempts you", lowered)
    if ring_match:
        return [{"action": "ring_tempts_you"}]

    venture_match = re.fullmatch(r"venture into the dungeon", lowered)
    if venture_match:
        return [{"action": "venture_into_the_dungeon"}]

    engines_match = re.fullmatch(r"start your engines!", lowered)
    if engines_match:
        return [{"action": "start_your_engines"}]

    energy_match = re.fullmatch(r"you get (\{e\}){2,}", lowered)
    if energy_match:
        amount = lowered.count("{e}")
        return [{"action": "get_energy", "amount": amount}]

    if "look at the top " in lowered:
        top_hand_match = re.fullmatch(
            r"look at the top (a|an|\w+) cards? of your library",
            lowered,
        )
        if top_hand_match:
            amount = parse_number(top_hand_match.group(1))
            return [{
                "action": "look_at_top_cards",
                "player": "you",
                "zone": "library",
                "count": amount or top_hand_match.group(1),
            }]
        return [{"action": "custom_effect", "text": normalized}]

    choose_to_hand_match = re.fullmatch(
        r"put (a|an|\w+) of them into your hand and the rest on the bottom of your library in any order",
        lowered,
    )
    if choose_to_hand_match:
        amount = parse_number(choose_to_hand_match.group(1))
        return [{
            "action": "move_selected_looked_at_cards",
            "selected_count": amount or choose_to_hand_match.group(1),
            "destination": "hand",
            "remainder_destination": "bottom_of_library",
            "remainder_order": "any",
        }]

    reveal_to_hand_match = re.fullmatch(
        r"reveal (a|an|any number of) (.+?) from among them and put (it|the revealed cards) into your hand",
        lowered,
    )
    if reveal_to_hand_match:
        quantifier = reveal_to_hand_match.group(1)
        selected_count: int | str = "any" if quantifier == "any number of" else 1
        effect = {
            "action": "move_selected_looked_at_cards",
            "selected_count": selected_count,
            "reveal": True,
            "filter": parse_card_filter_description(reveal_to_hand_match.group(2)),
            "destination": "hand",
        }
        if optional:
            effect["optional"] = True
        return [effect]

    put_rest_bottom_random_match = re.fullmatch(
        r"put the rest on the bottom of your library in a random order",
        lowered,
    )
    if put_rest_bottom_random_match:
        return [{
            "action": "move_unselected_looked_at_cards",
            "destination": "bottom_of_library",
            "order": "random",
        }]

    basic_land_tutor_match = re.fullmatch(
        r"search your library for a basic land card, reveal it, put it into your hand",
        lowered,
    )
    if basic_land_tutor_match:
        return [{
            "action": "search_library",
            "player": "you",
            "filter": {
                "card_types": ["Land"],
                "supertypes": ["Basic"],
            },
            "reveal": True,
            "destination": "hand",
        }]

    basic_land_ramp_match = re.fullmatch(
        r"search your library for a basic land card, put it onto the battlefield tapped",
        lowered,
    )
    if basic_land_ramp_match:
        return [{
            "action": "search_library",
            "player": "you",
            "filter": {
                "card_types": ["Land"],
                "supertypes": ["Basic"],
            },
            "destination": "battlefield",
            "tapped": True,
        }]

    put_it_hand_match = re.fullmatch(r"put it into your hand", lowered)
    if put_it_hand_match:
        return [{
            "action": "move_card",
            "object": "it",
            "destination_zone": "hand",
        }]

    then_shuffle_match = re.fullmatch(r"then shuffle", lowered)
    if then_shuffle_match:
        return [{"action": "shuffle_library", "player": "you"}]

    then_that_player_shuffles_match = re.fullmatch(r"then that player shuffles", lowered)
    if then_that_player_shuffles_match:
        return [{"action": "shuffle_library", "player": "that_player"}]

    that_player_shuffles_match = re.fullmatch(r"that player shuffles", lowered)
    if that_player_shuffles_match:
        return [{"action": "shuffle_library", "player": "that_player"}]

    shuffles_match = re.fullmatch(r"shuffles", lowered)
    if shuffles_match:
        return [{"action": "shuffle_library", "player": "that_player"}]

    shuffle_top_match = re.fullmatch(r"shuffle and put that card on top", lowered)
    if shuffle_top_match:
        return [{
            "action": "shuffle_and_move_revealed_card",
            "object": "that_card",
            "destination_zone": "top_of_library",
        }]

    put_rest_bottom_any_match = re.fullmatch(r"put the rest on the bottom of your library in any order", lowered)
    if put_rest_bottom_any_match:
        return [{
            "action": "move_unselected_looked_at_cards",
            "destination": "bottom_of_library",
            "order": "any",
        }]

    put_them_back_any_match = re.fullmatch(r"put them back in any order", lowered)
    if put_them_back_any_match:
        return [{
            "action": "return_looked_at_cards",
            "destination": "top_of_library",
            "order": "any",
        }]

    put_rest_gy_match = re.fullmatch(r"put the rest into your graveyard", lowered)
    if put_rest_gy_match:
        return [{
            "action": "move_unselected_looked_at_cards",
            "destination": "graveyard",
        }]

    reveal_top_match = re.fullmatch(r"reveal the top card of your library", lowered)
    if reveal_top_match:
        return [{"action": "reveal_top_card", "player": "you", "zone": "library"}]

    look_top_match = re.fullmatch(r"look at the top card of your library", lowered)
    if look_top_match:
        return [{"action": "look_at_top_cards", "player": "you", "zone": "library", "count": 1}]

    look_top_any_time_match = re.fullmatch(r"look at the top card of your library any time", lowered)
    if look_top_any_time_match:
        return [{"action": "look_at_top_card_any_time", "player": "you"}]

    play_that_card_this_turn_match = re.fullmatch(r"you may play that card this turn", lowered)
    if play_that_card_this_turn_match:
        return [{"action": "allow_play", "object": "that_card", "until": "end_of_turn"}]

    reveal_top_any_case_match = re.fullmatch(r"look at the top card of your library any time", lowered)
    if reveal_top_any_case_match:
        return [{"action": "look_at_top_card_any_time", "player": "you"}]

    draw_next_upkeep_match = re.fullmatch(r"draw a card at the beginning of the next turn's upkeep", lowered)
    if draw_next_upkeep_match:
        return [{
            "action": "create_delayed_trigger",
            "trigger": {"type": "beginning_of_next_turns_upkeep"},
            "condition": [],
            "effects": [{"action": "draw_cards", "amount": 1}],
        }]

    put_attacking_from_hand_match = re.fullmatch(
        r"put this card onto the battlefield from your hand tapped and attacking",
        lowered,
    )
    if put_attacking_from_hand_match:
        return [{
            "action": "move_card",
            "object": "self",
            "source_zone": "hand",
            "destination_zone": "battlefield",
            "tapped": True,
            "attacking": True,
        }]

    if "put the rest" in lowered:
        return [{"action": "custom_effect", "text": normalized}]

    delayed_sacrifice_match = re.fullmatch(
        r"sacrifice it at the beginning of the next end step",
        lowered,
    )
    if delayed_sacrifice_match:
        return [{
            "action": "create_delayed_trigger",
            "trigger": {"type": "beginning_of_next_end_step"},
            "condition": [],
            "effects": [
                {
                    "action": "sacrifice",
                    "target": "it",
                }
            ],
        }]

    if "exile that card instead of putting it into your graveyard as it resolves" in lowered:
        return [{
            "action": "replacement_effect",
            "text": normalized,
        }]

    if lowered == "exile it instead":
        return [{
            "action": "replacement_effect",
            "text": normalized,
        }]

    if lowered == "exile it":
        return [{"action": "exile", "target": "it"}]

    if lowered == "exile this saga":
        return [{"action": "exile", "target": "self"}]

    if lowered == "it can't be regenerated":
        return [{
            "action": "cant_be_regenerated",
            "target": "previous_target",
        }]

    if lowered == "they can't be regenerated":
        return [{
            "action": "cant_be_regenerated",
            "target": "previous_targets",
        }]

    if lowered == "play an additional land on each of your turns":
        return [{
            "action": "additional_land_play",
            "amount": 1,
            "scope": "each_of_your_turns",
            "optional": True,
        }]

    if "you may play an additional land" in lowered:
        return [{
            "action": "additional_land_play",
            "amount": 1,
            "scope": "each_of_your_turns",
        }]

    if lowered == "this land enters tapped":
        return [{
            "action": "enters_tapped",
            "target": "self",
        }]

    if lowered == "this artifact enters tapped":
        return [{"action": "enters_tapped", "target": "self"}]

    if lowered == "this creature enters tapped":
        return [{"action": "enters_tapped", "target": "self"}]

    if lowered == "it enters tapped":
        return [{"action": "enters_tapped", "target": "it"}]

    if lowered == "this spell can't be countered":
        return [{
            "action": "cant_be_countered",
            "target": "self_spell",
        }]

    if lowered == "this creature can't block":
        return [{
            "action": "combat_restriction",
            "target": "self",
            "restriction": "cant_block",
        }]

    if lowered == "this creature can't be blocked":
        return [{
            "action": "combat_restriction",
            "target": "self",
            "restriction": "cant_be_blocked",
        }]

    if lowered == "this creature attacks each combat if able":
        return [{
            "action": "attack_requirement",
            "target": "self",
            "requirement": "each_combat_if_able",
        }]

    if lowered == "target creature can't block this turn":
        return [{
            "action": "combat_restriction_until_end_of_turn",
            "target": "target_creature",
            "restriction": "cant_block",
        }]

    if lowered == "this creature can't be blocked this turn":
        return [{
            "action": "combat_restriction_until_end_of_turn",
            "target": "self",
            "restriction": "cant_be_blocked",
        }]

    if lowered == "target creature can't be blocked this turn":
        return [{
            "action": "combat_restriction_until_end_of_turn",
            "target": "target_creature",
            "restriction": "cant_be_blocked",
        }]

    if lowered == "this creature can block only creatures with flying":
        return [{
            "action": "combat_restriction",
            "target": "self",
            "restriction": "block_only_creatures_with_flying",
        }]

    if lowered == "it's still a land":
        return [{
            "action": "retain_card_type",
            "target": "previous_target",
            "card_type": "Land",
        }]

    if lowered == "enchanted creature doesn't untap during its controller's untap step":
        return [{
            "action": "untap_restriction",
            "target": "enchanted_creature",
            "scope": "controllers_untap_step",
        }]

    if lowered == "this creature doesn't untap during your untap step":
        return [{
            "action": "untap_restriction",
            "target": "self",
            "scope": "your_untap_step",
        }]

    if lowered == "you may choose not to untap this creature during your untap step":
        return [{
            "action": "optional_untap_restriction",
            "target": "self",
            "scope": "your_untap_step",
        }]

    if lowered == "you control enchanted creature":
        return [{
            "action": "gain_control",
            "target": "enchanted_creature",
            "duration": "static",
        }]

    if lowered == "enchanted creature has flying":
        return [{
            "action": "grant_keyword",
            "target": "enchanted_creature",
            "keyword": "flying",
        }]

    anthem_match = re.fullmatch(r"creatures you control get ([+-]\d+)/([+-]\d+) until end of turn", lowered)
    if anthem_match:
        return [{
            "action": "modify_stats_until_end_of_turn",
            "target": {"selector": "creatures_you_control"},
            "power_delta": int(anthem_match.group(1)),
            "toughness_delta": int(anthem_match.group(2)),
        }]

    static_anthem_match = re.fullmatch(r"creatures you control get ([+-]\d+)/([+-]\d+)", lowered)
    if static_anthem_match:
        return [{
            "action": "modify_stats",
            "target": {"selector": "creatures_you_control"},
            "power_delta": int(static_anthem_match.group(1)),
            "toughness_delta": int(static_anthem_match.group(2)),
        }]

    gain_life_that_much_match = re.fullmatch(r"you gain that much life", lowered)
    if gain_life_that_much_match:
        return [{"action": "gain_life", "player": "you", "amount": "that_much"}]

    may_gain_life_match = re.fullmatch(r"you may gain (\d+) life", lowered)
    if may_gain_life_match:
        return [{"action": "gain_life", "player": "you", "amount": int(may_gain_life_match.group(1)), "optional": True}]

    lose_two_life_match = re.fullmatch(r"you lose 2 life", lowered)
    if lose_two_life_match:
        return [{"action": "lose_life", "target": "you", "amount": 2}]

    lose_one_life_match = re.fullmatch(r"you lose 1 life", lowered)
    if lose_one_life_match:
        return [{"action": "lose_life", "target": "you", "amount": 1}]

    that_player_loses_one_life_match = re.fullmatch(r"that player loses 1 life", lowered)
    if that_player_loses_one_life_match:
        return [{"action": "lose_life", "target": "that_player", "amount": 1}]

    if lowered == "enchanted creature can't attack or block":
        return [{
            "action": "combat_restriction",
            "target": "enchanted_creature",
            "restriction": "cant_attack_or_block",
        }]

    if "cast a permanent spell of each permanent type from your graveyard" in lowered:
        return [{
            "action": "cast_from_graveyard_by_permanent_type",
            "scope": "each_of_your_turns",
        }]

    cast_from_graveyard_match = re.fullmatch(
        r"(?:you may )?cast this card from your graveyard by discarding (a|an|\w+) cards? in addition to paying its other costs",
        lowered,
    )
    if cast_from_graveyard_match:
        amount = parse_number(cast_from_graveyard_match.group(1))
        effect = {
            "action": "cast_from_graveyard",
            "object": "self",
            "additional_cost": {
                "action": "discard_cards",
                "amount": amount or cast_from_graveyard_match.group(1),
            },
        }
        if optional:
            effect["optional"] = True
        return [effect]

    return_self_battlefield_match = re.fullmatch(r"return this card from your graveyard to the battlefield", lowered)
    if return_self_battlefield_match:
        return [{
            "action": "return_from_graveyard_to_battlefield",
            "player": "you",
            "target": "self",
            "destination": "battlefield",
        }]

    return_self_hand_match = re.fullmatch(r"return this card from your graveyard to your hand", lowered)
    if return_self_hand_match:
        return [{
            "action": "move_card",
            "player": "you",
            "object": "self",
            "source_zone": "graveyard",
            "destination_zone": "hand",
        }]

    return_target_creature_hand_match = re.fullmatch(r"return target creature to its owner's hand", lowered)
    if return_target_creature_hand_match:
        return [{
            "action": "move_card",
            "target": {"selector": "target_creature"},
            "destination_zone": "hand",
            "owner": "its_owner",
        }]

    return_target_creature_from_graveyard_match = re.fullmatch(
        r"return target creature card from your graveyard to the battlefield",
        lowered,
    )
    if return_target_creature_from_graveyard_match:
        return [{
            "action": "return_from_graveyard_to_battlefield",
            "player": "you",
            "target": {
                "card_types": ["Creature"],
                "zone": "graveyard",
            },
            "destination": "battlefield",
        }]

    return_target_creature_to_hand_match = re.fullmatch(
        r"return target creature card from your graveyard to your hand",
        lowered,
    )
    if return_target_creature_to_hand_match:
        return [{
            "action": "move_card",
            "target": {"selector": "target_creature_card_in_your_graveyard"},
            "destination_zone": "hand",
        }]

    return_target_instant_sorcery_to_hand_match = re.fullmatch(
        r"return target instant or sorcery card from your graveyard to your hand",
        lowered,
    )
    if return_target_instant_sorcery_to_hand_match:
        return [{
            "action": "move_card",
            "target": {"selector": "target_instant_or_sorcery_card_in_your_graveyard"},
            "destination_zone": "hand",
        }]

    return_this_creature_hand_match = re.fullmatch(r"return this creature to its owner's hand", lowered)
    if return_this_creature_hand_match:
        return [{
            "action": "move_card",
            "target": "self",
            "destination_zone": "hand",
            "owner": "its_owner",
        }]

    return_it_owner_hand_match = re.fullmatch(r"return it to its owner's hand", lowered)
    if return_it_owner_hand_match:
        return [{
            "action": "move_card",
            "target": "it",
            "destination_zone": "hand",
            "owner": "its_owner",
        }]

    return_owner_control_match = re.fullmatch(r"return it to the battlefield under its owner's control", lowered)
    if return_owner_control_match:
        return [{
            "action": "move_card",
            "target": "it",
            "destination_zone": "battlefield",
            "controller": "its_owner",
        }]

    return_that_card_owner_control_match = re.fullmatch(
        r"return that card to the battlefield under its owner's control",
        lowered,
    )
    if return_that_card_owner_control_match:
        return [{
            "action": "move_card",
            "target": "that_card",
            "destination_zone": "battlefield",
            "controller": "its_owner",
        }]

    return_transformed_owner_control_match = re.fullmatch(
        r"return this card transformed under its owner's control",
        lowered,
    )
    if return_transformed_owner_control_match:
        return [{
            "action": "move_card",
            "target": "self",
            "destination_zone": "battlefield",
            "controller": "its_owner",
            "transformed": True,
        }]

    return_transformed_your_control_match = re.fullmatch(
        r"return it to the battlefield transformed under your control",
        lowered,
    )
    if return_transformed_your_control_match:
        return [{
            "action": "move_card",
            "target": "it",
            "destination_zone": "battlefield",
            "controller": "you",
            "transformed": True,
        }]

    return_tapped_self_match = re.fullmatch(r"return this card from your graveyard to the battlefield tapped", lowered)
    if return_tapped_self_match:
        return [{
            "action": "return_from_graveyard_to_battlefield",
            "player": "you",
            "target": "self",
            "destination": "battlefield",
            "tapped": True,
        }]

    sorcery_flash_match = re.fullmatch(r"(?:you may )?cast sorcery spells as though they had flash", lowered)
    if sorcery_flash_match:
        effect = {
            "action": "grant_cast_timing_override",
            "player": "you",
            "object": {"card_types": ["Sorcery"]},
            "as_though_had": "flash",
        }
        if optional:
            effect["optional"] = True
        return [effect]

    if lowered == "unearth only as a sorcery":
        return [{
            "action": "activation_restriction",
            "condition": [{"timing": "sorcery_speed"}],
        }]

    if lowered == "station only as a sorcery":
        return [{
            "action": "activation_restriction",
            "condition": [{"timing": "sorcery_speed"}],
        }]

    if lowered == "saddle only as a sorcery":
        return [{
            "action": "activation_restriction",
            "condition": [{"timing": "sorcery_speed"}],
        }]

    if lowered == "craft only as a sorcery":
        return [{
            "action": "activation_restriction",
            "condition": [{"timing": "sorcery_speed"}],
        }]

    if lowered == "exile it at the beginning of the next end step or if it would leave the battlefield":
        return [{
            "action": "temporary_reanimation_clause",
            "target": "it",
            "expire_at": "beginning_of_next_end_step",
            "exile_if_would_leave_battlefield": True,
        }]

    if lowered == "exile it at the beginning of the next end step":
        return [{
            "action": "create_delayed_trigger",
            "trigger": {"type": "beginning_of_next_end_step"},
            "condition": [],
            "effects": [{"action": "exile", "target": "it"}],
        }]

    if lowered == "(you may cast either half. that door unlocks on the battlefield. as a sorcery, you may pay the mana cost of a locked door to unlock it.)":
        return [{"action": "ignored_effect"}]

    if lowered == "any player may activate this ability":
        return [{
            "action": "activation_permission",
            "player_scope": "any_player",
        }]

    if lowered == "prevent all combat damage that would be dealt this turn":
        return [{
            "action": "prevent_damage",
            "scope": "all_combat_damage_this_turn",
        }]

    if lowered == "you win the game":
        return [{"action": "win_the_game"}]

    if lowered == "you lose the game":
        return [{"action": "lose_the_game"}]

    zone_cost_reduction_match = re.fullmatch(
        r"as long as (.+?) is in the command zone or on the battlefield, other (.+?) spells you cast cost (\{[^}]+\}) less to cast",
        lowered,
    )
    if zone_cost_reduction_match:
        amount = parse_number(zone_cost_reduction_match.group(3))
        effect = {
            "action": "cost_reduction",
            "player": "you",
            "object": {
                "kind": "spells",
                "exclude_self": True,
                "subtypes": [_normalize_subtype_word(word) for word in zone_cost_reduction_match.group(2).split() if word],
            },
            "amount": amount or zone_cost_reduction_match.group(3),
            "condition": [
                {
                    "subject": normalize_subject(zone_cost_reduction_match.group(1), card_name),
                    "zones_any": ["command_zone", "battlefield"],
                }
            ],
        }
        if optional:
            effect["optional"] = True
        return [effect]

    if "have cascade" in lowered:
        return [{
            "action": "grant_keyword",
            "keyword": "cascade",
            "text": normalized,
        }]

    if "have vigilance" in lowered:
        return [{
            "action": "grant_keyword",
            "target": "other_creatures_you_control" if lowered.startswith("other creatures you control") else "custom",
            "keyword": "vigilance",
        }]

    return []


def parse_effects_text(text: str, card_name: str) -> list[dict[str, Any]]:
    effects: list[dict[str, Any]] = []
    for sentence in split_sentences(text):
        clauses = maybe_split_conjoined_actions(sentence)
        parsed_any = False
        for clause in clauses:
            parsed = parse_effect_atom(clause, card_name)
            if parsed:
                filtered = [effect for effect in parsed if effect.get("action") != "ignored_effect"]
                if filtered:
                    effects.extend(filtered)
                    parsed_any = True
            elif len(clauses) == 1:
                effects.append({"action": "custom_effect", "text": clause})
                parsed_any = True
        if not parsed_any and not all(parse_effect_atom(clause, card_name) for clause in clauses):
            effects.append({"action": "custom_effect", "text": sentence})
    return effects


def parse_triggered_ability(text: str, card_name: str) -> dict[str, Any]:
    text = strip_ability_label(text)
    special_header = re.match(r"^((?:When|Whenever) you cast an Aura, Equipment, or Vehicle spell),\s*(.*)$", text, flags=re.IGNORECASE)
    if special_header:
        header = special_header.group(1).strip()
        remainder = special_header.group(2).strip()
    else:
        parts = text.split(",", 1)
        header = parts[0].strip()
        remainder = parts[1].strip() if len(parts) > 1 else ""

    trigger, conditions = parse_trigger_header(header, card_name)

    if remainder.lower().startswith("if "):
        if_match = re.match(r"if (.*?), (.*)", remainder, flags=re.IGNORECASE)
        if if_match:
            conditions.extend(parse_condition_fragment(if_match.group(1), card_name))
            remainder = if_match.group(2)

    ability: dict[str, Any] = {
        "raw_text": text,
        "trigger": trigger,
        "condition": conditions,
    }
    modal_payload = parse_modal_block(remainder, card_name)
    if modal_payload is not None:
        ability["effects"] = []
        ability.update(modal_payload)
        return ability

    ability["effects"] = parse_effects_text(remainder, card_name)
    return ability


def parse_activated_ability(text: str, card_name: str) -> dict[str, Any]:
    text = strip_ability_label(text)
    cost, effect_text = text.split(":", 1)
    modal_payload = parse_modal_block(effect_text, card_name)
    if modal_payload is not None:
        return {
            "raw_text": text,
            "cost": normalize_whitespace(cost),
            "condition": [],
            "effects": [],
            **modal_payload,
        }

    parsed_effects = parse_effects_text(effect_text, card_name)
    conditions: list[dict[str, Any]] = []
    remaining_effects: list[dict[str, Any]] = []

    for effect in parsed_effects:
        if effect.get("action") == "activation_restriction":
            conditions.extend(effect.get("condition", []))
        else:
            remaining_effects.append(effect)

    return {
        "raw_text": text,
        "cost": normalize_whitespace(cost),
        "condition": conditions,
        "effects": remaining_effects,
    }


def parse_equip_ability(text: str, card_name: str) -> dict[str, Any]:
    text = strip_ability_label(text)
    normalized = normalize_whitespace(text)
    reminder_stripped = strip_reminder_text(normalized)
    legendary_match = re.fullmatch(r"Equip legendary creature (\{[^}]+\})", reminder_stripped, re.IGNORECASE)
    if legendary_match:
        return {
            "raw_text": text,
            "cost": legendary_match.group(1),
            "condition": [{"timing": "sorcery_speed"}],
            "effects": [
                {
                    "action": "equip",
                    "target": {"selector": "target_creature_you_control", "supertypes": ["Legendary"]},
                }
            ],
        }
    match = re.fullmatch(r"Equip\s+(\{[^}]+\})", reminder_stripped, re.IGNORECASE)

    if not match:
        return {
            "raw_text": text,
            "cost": "",
            "condition": [],
            "effects": [{"action": "custom_effect", "text": reminder_stripped or normalized}],
        }

    return {
        "raw_text": text,
        "cost": match.group(1),
        "condition": [{"timing": "sorcery_speed"}],
        "effects": [
            {
                "action": "equip",
                "target": {"selector": "target_creature_you_control"},
            }
        ],
    }


def parse_crew_ability(text: str, card_name: str) -> dict[str, Any]:
    text = strip_ability_label(text)
    normalized = normalize_whitespace(text)
    reminder_stripped = strip_reminder_text(normalized)
    match = re.fullmatch(r"Crew\s+(\d+)", reminder_stripped, re.IGNORECASE)

    if not match:
        return {
            "raw_text": text,
            "cost": "",
            "condition": [],
            "effects": [{"action": "custom_effect", "text": reminder_stripped or normalized}],
        }

    return {
        "raw_text": text,
        "cost": {
            "action": "tap_creatures_with_total_power",
            "amount_gte": int(match.group(1)),
            "target": {"selector": "creatures_you_control"},
        },
        "condition": [],
        "effects": [
            {
                "action": "crew",
                "target": "self",
                "amount": int(match.group(1)),
            }
        ],
    }


def parse_static_ability(text: str, card_name: str) -> dict[str, Any]:
    stripped = strip_ability_label(text)
    modal_payload = parse_modal_block(stripped, card_name)
    if modal_payload is not None:
        return {
            "raw_text": text,
            "effects": [],
            **modal_payload,
        }

    parsed_effects = parse_effects_text(stripped, card_name)
    return {
        "raw_text": text,
        "effects": parsed_effects if parsed_effects else [{"action": "custom_effect", "text": text}],
    }


def parse_face(face: dict[str, Any]) -> dict[str, Any]:
    card_name = face["name"]
    static_keywords: list[dict[str, Any]] = []
    triggered: list[dict[str, Any]] = []
    activated: list[dict[str, Any]] = []
    static_abilities: list[dict[str, Any]] = []

    for ability in split_abilities(face["oracle_text"]):
        if not strip_reminder_text(ability).strip():
            continue

        if ability.lower().startswith(SAGA_REMINDER_PREFIX):
            continue

        keywords = parse_keywords_line(ability)
        if keywords is not None:
            static_keywords.extend(keywords)
            continue

        saga_chapter = parse_saga_chapter_ability(ability, card_name)
        if saga_chapter is not None:
            triggered.append(saga_chapter)
            continue

        normalized = strip_ability_label(ability)
        lowered = normalized.lower()

        if lowered.startswith("equip abilities you activate cost "):
            static_abilities.append(parse_static_ability(ability, card_name))
            continue

        if lowered.startswith("equip "):
            activated.append(parse_equip_ability(ability, card_name))
            continue

        if lowered.startswith("crew "):
            activated.append(parse_crew_ability(ability, card_name))
            continue

        if ":" in normalized and not lowered.startswith(("when ", "whenever ", "at ")):
            activated.append(parse_activated_ability(ability, card_name))
            continue

        if lowered.startswith(("when ", "whenever ", "at ")):
            triggered.append(parse_triggered_ability(ability, card_name))
            continue

        if lowered.startswith("during "):
            static_abilities.append(parse_static_ability(ability, card_name))
            continue

        static_abilities.append(parse_static_ability(ability, card_name))

    return {
        "name": face["name"],
        "type_line": face["type_line"],
        "oracle_text": face["oracle_text"] or "",
        "static": static_keywords,
        "triggered": triggered,
        "activated": activated,
        "static_abilities": static_abilities,
    }


def load_cards(commander_only: bool = False) -> list[dict[str, Any]]:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    where_clause = """
        where exists (
            select 1
            from card_faces cf
            where cf.parent_id = c.oracle_id
              and (
                cf.type_line like '%Legendary%Creature%'
                or lower(coalesce(cf.oracle_text, '')) like '%can be your commander%'
              )
        )
    """ if commander_only else ""

    cur.execute(
        f"""
        select
            c.oracle_id,
            c.name as card_name,
            c.layout,
            f.name as face_name,
            f.type_line,
            f.oracle_text
        from cards c
        join card_faces f on f.parent_id = c.oracle_id
        {where_clause}
        order by c.name, f.name
        """
    )

    cards: dict[str, dict[str, Any]] = {}
    for row in cur.fetchall():
        oracle_id = row["oracle_id"]
        card = cards.setdefault(
            oracle_id,
            {
                "oracle_id": oracle_id,
                "name": row["card_name"],
                "layout": row["layout"],
                "faces": [],
            },
        )
        card["faces"].append(
            {
                "name": row["face_name"],
                "type_line": row["type_line"],
                "oracle_text": row["oracle_text"],
            }
        )

    conn.close()
    return list(cards.values())


def load_commanders() -> list[dict[str, Any]]:
    return load_cards(commander_only=True)


def export_cards(output_dir: Path = CARD_OUTPUT_DIR, commander_only: bool = False) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    cards = load_cards(commander_only=commander_only)

    for existing in output_dir.glob("*.json"):
        existing.unlink()

    for card in cards:
        payload = {
            "schema_version": 1,
            "oracle_id": card["oracle_id"],
            "name": card["name"],
            "faces": [parse_face(face) for face in card["faces"]],
        }

        output_path = output_dir / filename_for_card(card["name"])
        output_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )

    return len(cards)


def export_commanders(output_dir: Path = COMMANDER_OUTPUT_DIR) -> int:
    return export_cards(output_dir=output_dir, commander_only=True)


if __name__ == "__main__":
    count = export_commanders()
    print(f"Exported {count} commander files to {COMMANDER_OUTPUT_DIR}")
