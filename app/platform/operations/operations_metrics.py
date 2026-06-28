from __future__ import annotations

from typing import Dict, List

from app.platform.operations.operations_models import DashboardPanel, OperationsIncident


def operations_metrics(panels: List[DashboardPanel], incidents: List[OperationsIncident]) -> Dict[str, int]:
    degraded = len([panel for panel in panels if panel.status == "degraded"])
    open_count = len([incident for incident in incidents if incident.status == "open"])
    return {
        "panel_count": len(panels),
        "degraded_panel_count": degraded,
        "incident_count": len(incidents),
        "open_incident_count": open_count,
    }
