from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class WorkItem:
    item_id: str
    tenant_id: str
    title: str
    item_type: str
    status: str
    owner: str


@dataclass(frozen=True)
class WorkStep:
    step_id: str
    item_id: str
    title: str
    status: str
    order: int


@dataclass(frozen=True)
class WorkNote:
    note_id: str
    item_id: str
    author: str
    body: str


@dataclass(frozen=True)
class WorkSummary:
    item_count: int
    open_count: int
    done_count: int
    step_count: int
    note_count: int


@dataclass(frozen=True)
class WorkContext:
    items: List[WorkItem]
    steps: List[WorkStep]
    notes: List[WorkNote]
    metadata: Dict[str, object]
