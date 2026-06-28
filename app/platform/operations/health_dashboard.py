from __future__ import annotations

from typing import Dict, List

from app.platform.operations.operations_models import DashboardPanel


def health_panel(checks: List[Dict[str, object]]) -> DashboardPanel:
    failed = len([check for check in checks if check.get("passed") is False])
    status = "healthy" if failed == 0 else "degraded"
    return DashboardPanel(
        panel_id="platform_health",
        title="Platform Health",
        status=status,
        value=f"{failed} failed checks",
    )
