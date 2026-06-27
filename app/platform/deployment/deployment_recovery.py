from __future__ import annotations

from app.platform.deployment.deployment_models import DeploymentResult


RETRY_DEPLOYMENT = "retry_deployment"
ROLLBACK_DEPLOYMENT = "rollback_deployment"
NO_RECOVERY = "no_recovery"


def deployment_recovery_action(result: DeploymentResult) -> str:
    if result.status == "completed":
        return NO_RECOVERY
    if "temporary" in result.error.lower() or "timeout" in result.error.lower():
        return RETRY_DEPLOYMENT
    return ROLLBACK_DEPLOYMENT
