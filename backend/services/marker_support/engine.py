from __future__ import annotations

import importlib.util
from functools import lru_cache
from pathlib import Path
from types import ModuleType

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from models.card import Card
from models.marker import CardMarker, Marker
from services.marker_support.profile_registry import MARKER_PROFILE_PATHS
from services.marker_support.types import MarkerProfileDefinition


@lru_cache(maxsize=None)
def load_marker_profile(marker_id: str) -> MarkerProfileDefinition:
    profile_path = MARKER_PROFILE_PATHS[marker_id]
    if not Path(profile_path).is_file():
        raise FileNotFoundError(f"Marker profile not found: {profile_path}")
    spec = importlib.util.spec_from_file_location(f"marker_profile_{marker_id.replace('-', '_')}", profile_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load marker profile from {profile_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return _profile_definition(module, marker_id)


def _profile_definition(module: ModuleType, configured_id: str) -> MarkerProfileDefinition:
    marker_id = getattr(module, "MARKER_ID", None)
    name = getattr(module, "MARKER_NAME", None)
    description = getattr(module, "MARKER_DESCRIPTION", None)
    matches = getattr(module, "matches", None)
    if marker_id != configured_id:
        raise ValueError(f"Marker profile {configured_id!r} must declare the same MARKER_ID.")
    if not isinstance(name, str) or not name.strip() or not isinstance(description, str) or not description.strip():
        raise ValueError(f"Marker profile {configured_id!r} requires nonempty name and description.")
    if not callable(matches):
        raise ValueError(f"Marker profile {configured_id!r} requires matches(card).")
    return MarkerProfileDefinition(marker_id, name, description, matches)


def marker_profiles() -> tuple[MarkerProfileDefinition, ...]:
    profiles = tuple(load_marker_profile(marker_id) for marker_id in MARKER_PROFILE_PATHS)
    ids = [profile.marker_id for profile in profiles]
    if len(ids) != len(set(ids)):
        raise ValueError("Marker profile IDs must be unique.")
    return profiles


def sync_marker_membership(session: Session, marker_id: str, oracle_ids: set[str]) -> int:
    existing = set(session.scalars(select(CardMarker.oracle_id).where(CardMarker.marker_id == marker_id)))
    stale = existing - oracle_ids
    added = oracle_ids - existing
    if stale:
        session.execute(delete(CardMarker).where(CardMarker.marker_id == marker_id, CardMarker.oracle_id.in_(stale)))
    session.add_all(CardMarker(marker_id=marker_id, oracle_id=oracle_id) for oracle_id in added)
    return len(stale) + len(added)


def refresh_markers(session: Session) -> int:
    cards = session.scalars(select(Card).options(selectinload(Card.faces))).all()
    changes = 0
    for profile in marker_profiles():
        marker = session.get(Marker, profile.marker_id)
        if marker is None:
            session.add(Marker(id=profile.marker_id, name=profile.name, description=profile.description))
        else:
            marker.name = profile.name
            marker.description = profile.description
        matching_ids = {card.oracle_id for card in cards if profile.matches(card)}
        changes += sync_marker_membership(session, profile.marker_id, matching_ids)
    session.flush()
    return changes
