from __future__ import annotations

from typing import Dict

ERROR_MESSAGES: Dict[str, str] = {
    "bad_request": "Request is invalid.",
    "unauthorized": "Authentication is required.",
    "forbidden": "Access is not allowed.",
    "not_found": "Resource was not found.",
    "conflict": "Resource state conflicts with the request.",
    "rate_limited": "Request rate limit exceeded.",
    "internal_error": "Internal service error.",
}


def supported_error_codes() -> list:
    return sorted(ERROR_MESSAGES)


def error_message(code: str) -> str:
    return ERROR_MESSAGES.get(code, ERROR_MESSAGES["internal_error"])


def is_supported_error_code(code: str) -> bool:
    return code in ERROR_MESSAGES
