from __future__ import annotations

from typing import Dict, Optional

from app.platform.api_gateway.api_models import ApiEndpoint
from app.platform.api_gateway.api_registry import api_registry


def route_table() -> Dict[str, ApiEndpoint]:
    return {endpoint.path: endpoint for endpoint in api_registry().values()}


def resolve_route(path: str) -> Optional[ApiEndpoint]:
    return route_table().get(path)


def registered_paths() -> list:
    return sorted(route_table())
