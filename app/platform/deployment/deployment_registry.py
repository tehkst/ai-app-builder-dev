from __future__ import annotations

from typing import Dict

from app.platform.deployment.deployment_models import DeploymentPlan


def deployment_registry() -> Dict[str, DeploymentPlan]:
    plan = DeploymentPlan(
        plan_id="local_deployment_plan",
        application_id="ai_software_factory",
        target_id="local_dev",
        strategy="validate_then_release",
        steps=["validate", "package", "release"],
        metadata={"vendor_neutral": True},
    )
    return {plan.plan_id: plan}


def find_deployment_plan(plan_id: str) -> DeploymentPlan:
    return deployment_registry()[plan_id]
