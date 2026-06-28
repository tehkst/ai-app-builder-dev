from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class OperationsIncident:
    incident_id: str
    severity: str
    source: str
    status: str
    summary: str
    metadata: Dict[str, object]


@dataclass(frozen=True)
class DashboardPanel:
    panel_id: str
    title: str
    status: str
    value: str
