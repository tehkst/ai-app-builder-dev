from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class DeploymentTarget:
    target_id: str
    target_type: str
    environment: str
    provider: str
    active: bool = True


@dataclass(frozen=True)
class DeploymentPlan:
    plan_id: str
    application_id: str
    target_id: str
    strategy: str
    steps: List[str]
    metadata: Dict[str, object]


@dataclass(frozen=True)
class DeploymentResult:
    plan_id: str
    status: str
    completed_steps: List[str]
    error: str = ""
