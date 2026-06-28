from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class FeedEvent:
    event_id: str
    tenant_id: str
    source: str
    actor: str
    action: str
    target: str
    severity: str
    created_at: str


@dataclass(frozen=True)
class FeedSummary:
    event_count: int
    tenant_event_count: int
    high_count: int
    lifecycle_count: int
    catalog_count: int
    task_count: int


@dataclass(frozen=True)
class FeedContext:
    events: List[FeedEvent]
    metadata: Dict[str, object]
