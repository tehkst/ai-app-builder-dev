from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class Scenario:
    name: str
    assumptions: dict[str, Any] = field(default_factory=dict)


@dataclass
class SimulationSession:
    scenario: Scenario
    session_id: str = field(default_factory=lambda: "SIM-{}".format(uuid4().hex.upper()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "ready"
