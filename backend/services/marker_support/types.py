from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from models.card import Card


@dataclass(frozen=True)
class MarkerProfileDefinition:
    marker_id: str
    name: str
    description: str
    matches: Callable[[Card], bool]
