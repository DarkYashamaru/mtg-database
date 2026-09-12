from __future__ import annotations

from database.session import session_scope
from services.marker_support.engine import refresh_markers


def import_markers() -> int:
    """Synchronize all registered marker profiles and their card memberships."""
    with session_scope() as session:
        return refresh_markers(session)
