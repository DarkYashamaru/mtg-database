from __future__ import annotations

from oracle_card_parser import COMMANDER_OUTPUT_DIR, export_commanders


if __name__ == "__main__":
    count = export_commanders()
    print(f"Exported {count} commander files to {COMMANDER_OUTPUT_DIR}")
