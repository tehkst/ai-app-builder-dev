from __future__ import annotations

from typing import List

from app.platform.deployment.deployment_models import DeploymentResult
from app.platform.saas_portal.portal_models import PortalCard, PortalView


def portal_deployment_view(results: List[DeploymentResult]) -> PortalView:
    completed = len([result for result in results if result.status == "completed"])
    failed = len([result for result in results if result.status == "failed"])
    cards = [
        PortalCard("customer_deployments_completed", "Completed Deployments", str(completed), "healthy", {}),
        PortalCard("customer_deployments_failed", "Failed Deployments", str(failed), "degraded" if failed else "healthy", {}),
    ]
    return PortalView("deployment_view", "Deployments", cards)
