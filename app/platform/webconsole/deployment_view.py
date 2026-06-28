from __future__ import annotations

from typing import List

from app.platform.deployment.deployment_models import DeploymentResult
from app.platform.webconsole.console_models import ConsoleCard, ConsoleView


def deployment_view(results: List[DeploymentResult]) -> ConsoleView:
    completed = len([result for result in results if result.status == "completed"])
    failed = len([result for result in results if result.status == "failed"])
    cards = [
        ConsoleCard("deployments_completed", "Completed Deployments", str(completed), "healthy", {}),
        ConsoleCard("deployments_failed", "Failed Deployments", str(failed), "degraded" if failed else "healthy", {}),
    ]
    return ConsoleView("deployment_view", "Deployments", cards)
