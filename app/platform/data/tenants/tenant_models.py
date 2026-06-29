from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict


@dataclass(frozen=True)
class Tenant:
    tenant_id: str
    name: str
    lifecycle: str = "enabled"
    plan: str = "starter"
    metadata: Dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def enabled(self) -> bool:
        return self.lifecycle == "enabled"
