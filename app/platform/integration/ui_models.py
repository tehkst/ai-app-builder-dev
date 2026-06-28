from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class SharedStatusCard:
    card_id: str
    title: str
    value: str
    status: str
    metadata: Dict[str, object]


@dataclass(frozen=True)
class SharedNavigationItem:
    item_id: str
    title: str
    route: str
    audience: str
    source: str
