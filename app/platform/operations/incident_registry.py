from __future__ import annotations

from typing import Dict, List

from app.platform.operations.operations_models import OperationsIncident


def incident_registry() -> Dict[str, OperationsIncident]:
    return {}


def add_incident(registry: Dict[str, OperationsIncident], incident: OperationsIncident) -> Dict[str, OperationsIncident]:
    updated = dict(registry)
    updated[incident.incident_id] = incident
    return updated


def open_incidents(registry: Dict[str, OperationsIncident]) -> List[OperationsIncident]:
    return [incident for incident in registry.values() if incident.status == "open"]
