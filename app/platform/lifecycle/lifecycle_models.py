from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class LifecycleStage:
    stage_id: str
    title: str
    sequence: int
    service_owner: str
    required_artifact: str


@dataclass(frozen=True)
class LifecycleApplication:
    application_id: str
    tenant_id: str
    name: str
    current_stage: str
    status: str
    owner: str


@dataclass(frozen=True)
class LifecycleEvent:
    event_id: str
    application_id: str
    stage_id: str
    actor: str
    action: str
    status: str
    metadata: Dict[str, object]


@dataclass(frozen=True)
class LifecyclePlan:
    application: LifecycleApplication
    stages: List[LifecycleStage]
    events: List[LifecycleEvent]


@dataclass(frozen=True)
class LifecycleSummary:
    application_count: int
    active_count: int
    stage_count: int
    event_count: int
    completed_stage_count: int
