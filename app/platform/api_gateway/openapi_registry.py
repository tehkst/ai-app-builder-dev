from __future__ import annotations

from typing import Dict, List

from app.platform.api_gateway.api_errors import supported_error_codes
from app.platform.api_gateway.api_registry import api_registry


REQUIRED_HEADERS = [
    "x-tenant-id",
    "x-actor-id",
    "x-request-id",
    "x-trace-id",
]


def openapi_parameters() -> List[Dict[str, object]]:
    return [
        {
            "name": header,
            "in": "header",
            "required": True,
            "schema": {"type": "string"},
        }
        for header in REQUIRED_HEADERS
    ]


def openapi_paths() -> Dict[str, Dict[str, object]]:
    paths: Dict[str, Dict[str, object]] = {}
    for endpoint in api_registry().values():
        paths.setdefault(endpoint.path, {})[endpoint.method.lower()] = {
            "summary": endpoint.description,
            "tags": [endpoint.domain],
            "parameters": openapi_parameters(),
            "responses": {
                "200": {
                    "description": "Standard API gateway response",
                },
                "400": {
                    "description": "Standard API gateway error response",
                },
            },
            "x-error-codes": supported_error_codes(),
        }
    return paths


def openapi_document() -> Dict[str, object]:
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "AI Software Factory Enterprise API Gateway",
            "version": "v1",
        },
        "paths": openapi_paths(),
    }
