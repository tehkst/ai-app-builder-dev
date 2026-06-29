from __future__ import annotations

from app.platform.api_gateway.agent_api import agent_summary
from app.platform.api_gateway.api_context import ApiRequestContext, context_from_headers
from app.platform.api_gateway.api_registry import api_registry, endpoints_by_domain
from app.platform.api_gateway.api_response import error_response, ok_response, response_error_messages
from app.platform.api_gateway.api_router import registered_paths, resolve_route
from app.platform.api_gateway.api_versioning import is_supported_version, versioned_path
from app.platform.api_gateway.deployment_api import deployment_summary
from app.platform.api_gateway.learning_api import learning_summary
from app.platform.api_gateway.openapi_registry import openapi_document, openapi_paths
from app.platform.api_gateway.operations_api import operations_summary
from app.platform.api_gateway.plugin_api import plugin_summary
from app.platform.api_gateway.registry_api import registry_summary
from app.platform.api_gateway.runtime_api import runtime_summary


def main() -> None:
    assert is_supported_version("v1") is True
    assert versioned_path("runtime") == "/api/v1/runtime"

    registry = api_registry()
    assert "runtime_list" in registry, registry
    assert len(registry) >= 7, registry
    assert endpoints_by_domain("runtime")[0].path == "/api/v1/runtime"

    paths = registered_paths()
    assert "/api/v1/runtime" in paths, paths
    assert resolve_route("/api/v1/runtime") is not None

    context = ApiRequestContext(
        tenant_id="tenant1",
        actor_id="actor1",
        request_id="request1",
        trace_id="trace1",
        idempotency_key="key1",
    )
    assert context.valid() is True
    assert context.headers()["x-tenant-id"] == "tenant1"
    assert context_from_headers(context.headers()) == context
    assert context_from_headers({}).valid() is False

    ok = ok_response({"status": "ok"})
    assert ok.success is True
    failed = error_response("bad_request", "Invalid request")
    assert failed.success is False
    assert response_error_messages(failed) == ["Invalid request"]

    assert runtime_summary().data["domain"] == "runtime"
    assert deployment_summary().data["domain"] == "deployment"
    assert operations_summary().data["domain"] == "operations"
    assert registry_summary().data["domain"] == "registry"
    assert plugin_summary().data["domain"] == "plugins"
    assert agent_summary().data["domain"] == "agents"
    assert learning_summary().data["domain"] == "learning"

    openapi = openapi_document()
    assert openapi["openapi"] == "3.0.0", openapi
    assert "/api/v1/runtime" in openapi_paths(), openapi

    print("API GATEWAY CHECK PASSED")


if __name__ == "__main__":
    main()
