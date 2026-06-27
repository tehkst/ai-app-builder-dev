from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class RuntimeWorker:
    worker_id: str
    agent_id: str
    capabilities: List[str]
    status: str
    active_job_count: int
