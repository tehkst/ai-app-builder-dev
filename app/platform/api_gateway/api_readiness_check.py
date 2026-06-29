from __future__ import annotations

from app.platform.api_gateway.api_context import ApiRequestContext
from app.platform.api_gateway.api_errors import supported_error_codes
from app.platform.api_gateway.api_registry import api_registry
from app.platform.api_gateway.api_runtime import validate_api_request
from app.platform.api_gateway.openapi_registry import openapi_paths


def main() -> None:
    registry = api_registry()
    paths = openapi_paths()
    assert registry, "API registry must not be empty"
    assert paths, "OpenAPI paths must not be empty"
    assert len(registry) == len(paths), (registry, paths)

    context = ApiRequestContext(
        tenant_id="tenant1",
        actor_id="actor1",
        request_id="request1",
        trace_id="trace1",
    )
    for endpoint in registry.values():
        assert endpoint.path in paths, endpoint
        result = validate_api_request(endpoint.path, context.headers())
        assert result.success is True, result
        assert result.data["endpoint_id"] == endpoint.endpoint_id
        assert result.data["domain"] == endpoint.domain

    assert {"bad_request", "not_found", "internal_error"}.issubset(set(supported_error_codes()))
    print("D4 API READINESS CHECK PASSED")


if __name__ == "__main__":
    main()
