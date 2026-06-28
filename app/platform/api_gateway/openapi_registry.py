from __future__ import annotations

from typing import Dict

from app.platform.api_gateway.api_registry import api_registry


def openapi_paths() -> Dict[str, Dict[str, object]]:
    paths: Dict[str, Dict[str, object]] = {}
    for endpoint in api_registry().values():
        paths.setdefault(endpoint.path, {})[endpoint.method.lower()] = {
            "summary": endpoint.description,
            "tags": [endpoint.domain],
            "responses": {
                "200": {
                    "description": "Standard API gateway response",
                }
            },
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
