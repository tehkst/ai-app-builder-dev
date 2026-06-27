from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DelegationRequest:
    request_id: str
    required_capability: str
    source_story_id: Optional[str]
    priority: int
