from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict


@dataclass(frozen=True)
class DataEvent:
    event_id: str
    tenant_id: str
    kind: str
    source: str
    target: str
    details: Dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def belongs_to(self, tenant_id: str) -> bool:
        return self.tenant_id == tenant_id
