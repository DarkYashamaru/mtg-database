from __future__ import annotations

from pathlib import Path
from pprint import pformat


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RELATIONSHIPS_PATH = PROJECT_ROOT / "relationships" / "archetypes_tags.md"
OUTPUT_PATH = PROJECT_ROOT / "backend" / "data" / "archetypes_data.py"
SEPARATOR = "====Archetypes to tags===="
SECTION_ALIASES = {
    "pp Counters (+1/+1 Counters)": "+1/+1 Counters",
}


def parse_archetypes_markdown(source_path: Path) -> dict[str, list[str]]:
    lines = source_path.read_text(encoding="utf-8").splitlines()
    separator_index = lines.index(SEPARATOR)

    headings: list[str] = []
    seen_headings: set[str] = set()
    for raw_line in lines[:separator_index]:
        line = raw_line.strip()
        if not line or line == SEPARATOR or line in seen_headings:
            continue
        headings.append(line)
        seen_headings.add(line)

    sections: dict[str, list[str]] = {heading: [] for heading in headings}
    current_heading: str | None = None

    for raw_line in lines[separator_index + 1 :]:
        line = raw_line.strip()
        if not line:
            continue

        normalized_heading = SECTION_ALIASES.get(line, line)
        if normalized_heading in sections:
            current_heading = normalized_heading
            continue

        if current_heading is None:
            continue

        sections[current_heading].append(line)

    return sections


def render_python_module(archetype_data: dict[str, list[str]]) -> str:
    rendered_data = pformat(archetype_data, width=88, sort_dicts=False)
    return (
        '"""Generated from relationships/archetypes_tags.md.\n\n'
        "Run backend/scripts/generate_archetypes_data.py to refresh this file after\n"
        "updating the relationships document.\n"
        '"""\n\n'
        f"ARCHETYPE_DATA = {rendered_data}\n"
    )


def main() -> int:
    archetype_data = parse_archetypes_markdown(RELATIONSHIPS_PATH)
    OUTPUT_PATH.write_text(render_python_module(archetype_data), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
