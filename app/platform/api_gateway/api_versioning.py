from __future__ import annotations

SUPPORTED_API_VERSIONS = ["v1"]
DEFAULT_API_VERSION = "v1"


def is_supported_version(version: str) -> bool:
    return version in SUPPORTED_API_VERSIONS


def versioned_path(path: str, version: str = DEFAULT_API_VERSION) -> str:
    clean_path = path if path.startswith("/") else f"/{path}"
    return f"/api/{version}{clean_path}"
