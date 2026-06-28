from __future__ import annotations

from typing import Dict, List

from app.platform.api_gateway.api_models import ApiEndpoint
from app.platform.api_gateway.api_versioning import versioned_path


def api_registry() -> Dict[str, ApiEndpoint]:
    endpoints = [
        ApiEndpoint("runtime_list", "GET", versioned_path("/runtime"), "runtime", "v1", "Runtime summary"),
        ApiEndpoint("deployment_list", "GET", versioned_path("/deployments"), "deployment", "v1", "Deployment summary"),
        ApiEndpoint("operations_list", "GET", versioned_path("/operations"), "operations", "v1", "Operations summary"),
        ApiEndpoint("registry_list", "GET", versioned_path("/registry"), "registry", "v1", "Registry summary"),
        ApiEndpoint("plugins_list", "GET", versioned_path("/plugins"), "plugins", "v1", "Plugin summary"),
        ApiEndpoint("agents_list", "GET", versioned_path("/agents"), "agents", "v1", "Agent summary"),
        ApiEndpoint("learning_list", "GET", versioned_path("/learning"), "learning", "v1", "Learning summary"),
    ]
    return {endpoint.endpoint_id: endpoint for endpoint in endpoints}


def endpoints_by_domain(domain: str) -> List[ApiEndpoint]:
    return [endpoint for endpoint in api_registry().values() if endpoint.domain == domain]
