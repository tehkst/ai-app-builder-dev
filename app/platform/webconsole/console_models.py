from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class ConsolePage:
    page_id: str
    title: str
    route: str
    section: str
    admin_only: bool = True


@dataclass(frozen=True)
class ConsoleCard:
    card_id: str
    title: str
    value: str
    status: str
    metadata: Dict[str, object]


@dataclass(frozen=True)
class ConsoleView:
    view_id: str
    title: str
    cards: List[ConsoleCard]
