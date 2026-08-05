from __future__ import annotations

from oracle_card_parser import CARD_OUTPUT_DIR, export_cards


if __name__ == "__main__":
    count = export_cards()
    print(f"Exported {count} card files to {CARD_OUTPUT_DIR}")
