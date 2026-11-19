from __future__ import annotations

import json

from database.session import session_scope
from downloaders.download_symbology import SYMBOLS_PATH
from models.color import ScryfallSymbol
from sqlalchemy import delete


def import_symbology() -> int:
    payload = json.loads(SYMBOLS_PATH.read_text(encoding="utf-8"))
    with session_scope() as session:
        session.execute(delete(ScryfallSymbol))
        rows = []
        for item in payload.get("data", []):
            if not isinstance(item, dict) or not isinstance(item.get("symbol"), str):
                continue
            rows.append(ScryfallSymbol(
                symbol=item["symbol"], svg_uri=item.get("svg_uri"), english=item.get("english") or "",
                transposable=bool(item.get("transposable")), appears_in_mana_costs=bool(item.get("appears_in_mana_costs")),
                mana_value=item.get("mana_value"), hybrid=bool(item.get("hybrid")), phyrexian=bool(item.get("phyrexian")),
                replaces=item.get("replaces"), funny=bool(item.get("funny")), hidden=bool(item.get("hidden")),
            ))
        session.add_all(rows)
        return len(rows)
