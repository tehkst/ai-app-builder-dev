from __future__ import annotations

from app.platform.api_gateway.api_response import ok_response
from app.platform.deployment.deployment_registry import deployment_registry


def deployment_summary():
    return ok_response({"domain": "deployment", "deployment_plan_count": len(deployment_registry())})
