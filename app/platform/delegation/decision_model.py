from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class DelegationDecision:
    request_id: str
    selected_agent_id: Optional[str]
    candidate_agent_ids: List[str]
    reason: str
    allowed: bool
