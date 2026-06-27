from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeProfile:
    agent_id: str
    status: str
    current_load: int
    queue_depth: int
    health_score: int
