from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.platform.runtime.job_state import CREATED


@dataclass(frozen=True)
class RuntimeJob:
    job_id: str
    workflow_id: str
    task_id: str
    required_capability: str
    priority: int
    state: str = CREATED
    assigned_agent_id: Optional[str] = None
    error: Optional[str] = None
