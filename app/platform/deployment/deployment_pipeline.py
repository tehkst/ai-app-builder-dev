from __future__ import annotations

from typing import Dict

from app.platform.deployment.deployment_engine import execute_deployment
from app.platform.deployment.deployment_models import DeploymentPlan


def run_pipeline(plan: DeploymentPlan) -> Dict[str, object]:
    result = execute_deployment(plan)
    return {
        "plan_id": result.plan_id,
        "status": result.status,
        "step_count": len(result.completed_steps),
    }
