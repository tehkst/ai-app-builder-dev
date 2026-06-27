from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class AgentProfile:
    agent_id: str
    department: str
    capabilities: List[str]
    status: str
    current_load: int
