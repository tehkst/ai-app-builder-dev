from __future__ import annotations

from typing import Dict

from app.platform.api_gateway.api_context import context_from_headers
from app.platform.api_gateway.api_response import error_response, ok_response
from app.platform.api_gateway.api_router import resolve_route


def validate_api_request(path: str, headers: Dict[str, str]) -> object:
    endpoint = resolve_route(path)
    if endpoint is None:
        return error_response("not_found")

    context = context_from_headers(headers)
    if not context.valid():
        return error_response("bad_request", "Missing required request context.")

    return ok_response(
        {
            "endpoint_id": endpoint.endpoint_id,
            "domain": endpoint.domain,
            "path": endpoint.path,
            "tenant_id": context.tenant_id,
            "request_id": context.request_id,
            "trace_id": context.trace_id,
        }
    )
