from __future__ import annotations

from app.platform.api_gateway.api_response import ok_response
from app.platform.registry.registry import base_registry


def registry_summary():
    registry = base_registry()
    return ok_response({"domain": "registry", "resource_count": len(registry)})
