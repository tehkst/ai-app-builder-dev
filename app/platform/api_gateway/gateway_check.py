from __future__ import annotations

from app.platform.api_gateway.agent_api import agent_summary
from app.platform.api_gateway.api_context import ApiRequestContext, context_from_headers
from app.platform.api_gateway.api_errors import error_message, is_supported_error_code, supported_error_codes
from app.platform.api_gateway.api_registry import api_registry, endpoints_by_domain
from app.platform.api_gateway.api_response import error_response, ok_response, response_error_messages
from app.platform.api_gateway.api_router import registered_paths, resolve_route
from app.platform.api_gateway.api_runtime import validate_api_request
from app.platform.api_gateway.api_versioning import is_supported_version, versioned_path
from app.platform.api_gateway.deployment_api import deployment_summary
from app.platform.api_gateway.learning_api import learning_summary
from app.platform.api_gateway.openapi_registry import openapi_document, openapi_parameters, openapi_paths
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

    runtime_result = validate_api_request("/api/v1/runtime", context.headers())
    assert runtime_result.success is True
    assert runtime_result.data["tenant_id"] == "tenant1"
    missing_context = validate_api_request("/api/v1/runtime", {})
    assert missing_context.success is False
    assert missing_context.errors[0].code == "bad_request"
    missing_route = validate_api_request("/api/v1/missing", context.headers())
    assert missing_route.success is False
    assert missing_route.errors[0].code == "not_found"

    assert is_supported_error_code("bad_request") is True
    assert "bad_request" in supported_error_codes()
    assert error_message("unknown") == error_message("internal_error")

    ok = ok_response({"status": "ok"})
    assert ok.success is True
    failed = error_response("bad_request", "Invalid request")
    assert failed.success is False
    assert failed.errors[0].code == "bad_request"
    assert response_error_messages(failed) == ["Invalid request"]
    fallback = error_response("unknown")
    assert fallback.errors[0].code == "internal_error"

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
    assert len(openapi_parameters()) == 4
    runtime_get = openapi_paths()["/api/v1/runtime"]["get"]
    assert runtime_get["parameters"][0]["in"] == "header"
    assert "bad_request" in runtime_get["x-error-codes"]

    print("API GATEWAY CHECK PASSED")


if __name__ == "__main__":
    main()
