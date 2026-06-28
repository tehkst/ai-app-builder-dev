from __future__ import annotations

from typing import Dict

from app.platform.auth.authentication import authenticate_identity
from app.platform.auth.identity_provider import find_identity
from app.platform.deployment.deployment_engine import execute_deployment
from app.platform.deployment.deployment_planner import build_deployment_plan
from app.platform.operations.deployment_dashboard import deployment_panel


def login_deploy_observe_flow() -> Dict[str, object]:
    identity = find_identity("user_platform_owner")
    auth = authenticate_identity(identity, "org_platform", "tenant_platform")
    plan = build_deployment_plan("app", "local", "safe_release")
    result = execute_deployment(plan)
    panel = deployment_panel([result])
    return {
        "authenticated": auth.success,
        "tenant_id": auth.principal.tenant_id,
        "deployment_status": result.status,
        "operations_status": panel.status,
    }
