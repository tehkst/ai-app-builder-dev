from __future__ import annotations

from typing import Dict

from app.platform.api_gateway.deployment_api import deployment_summary
from app.platform.api_gateway.registry_api import registry_summary


def customer_api_overview() -> Dict[str, object]:
    deployment = deployment_summary()
    registry = registry_summary()
    return {
        "deployment_plan_count": deployment.data.get("deployment_plan_count", 0),
        "registry_resource_count": registry.data.get("resource_count", 0),
    }
