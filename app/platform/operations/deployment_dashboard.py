from __future__ import annotations

from typing import List

from app.platform.deployment.deployment_metrics import deployment_metrics
from app.platform.deployment.deployment_models import DeploymentResult
from app.platform.operations.operations_models import DashboardPanel


def deployment_panel(results: List[DeploymentResult]) -> DashboardPanel:
    metrics = deployment_metrics(results)
    failed = metrics.get("failed_deployment_count", 0)
    status = "healthy" if failed == 0 else "degraded"
    return DashboardPanel(
        panel_id="deployment_status",
        title="Deployment Status",
        status=status,
        value=f"{metrics['completed_deployment_count']} completed / {failed} failed",
    )
