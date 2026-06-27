from __future__ import annotations

from app.platform.deployment.deployment_models import DeploymentPlan, DeploymentResult


def execute_deployment(plan: DeploymentPlan) -> DeploymentResult:
    return DeploymentResult(
        plan_id=plan.plan_id,
        status="completed",
        completed_steps=list(plan.steps),
    )


def fail_deployment(plan: DeploymentPlan, error: str) -> DeploymentResult:
    return DeploymentResult(
        plan_id=plan.plan_id,
        status="failed",
        completed_steps=[],
        error=error,
    )
