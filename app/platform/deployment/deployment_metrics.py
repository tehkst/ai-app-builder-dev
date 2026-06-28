from __future__ import annotations

from typing import Dict, List

from app.platform.deployment.deployment_models import DeploymentResult


def deployment_metrics(results: List[DeploymentResult]) -> Dict[str, int]:
    completed = len([result for result in results if result.status == "completed"])
    failed = len([result for result in results if result.status == "failed"])
    return {
        "deployment_count": len(results),
        "completed_deployment_count": completed,
        "failed_deployment_count": failed,
    }
