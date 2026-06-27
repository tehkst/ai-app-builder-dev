from __future__ import annotations

from typing import List

from app.platform.deployment.deployment_models import DeploymentPlan


def build_deployment_plan(application_id: str, target_id: str, strategy: str = "validate_then_release") -> DeploymentPlan:
    steps: List[str] = ["validate", "package", "release"]
    if strategy == "safe_release":
        steps = ["validate", "package", "release", "verify"]
    return DeploymentPlan(
        plan_id=f"{application_id}_{target_id}_{strategy}",
        application_id=application_id,
        target_id=target_id,
        strategy=strategy,
        steps=steps,
        metadata={"vendor_neutral": True},
    )
