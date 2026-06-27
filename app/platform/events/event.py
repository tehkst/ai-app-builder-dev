from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class PlatformEvent:
    event_id: str
    event_type: str
    source: str
    payload: Dict[str, object]
    created_at: str
