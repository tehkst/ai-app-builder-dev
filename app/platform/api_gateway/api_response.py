from __future__ import annotations

from typing import Dict, List, Optional

from app.platform.api_gateway.api_errors import error_message, is_supported_error_code
from app.platform.api_gateway.api_models import ApiError, ApiResponse


def ok_response(data: Dict[str, object], version: str = "v1") -> ApiResponse:
    return ApiResponse(success=True, version=version, data=data, errors=[])


def error_response(code: str, message: Optional[str] = None, version: str = "v1") -> ApiResponse:
    resolved_code = code if is_supported_error_code(code) else "internal_error"
    return ApiResponse(
        success=False,
        version=version,
        data={},
        errors=[ApiError(code=resolved_code, message=message or error_message(resolved_code))],
    )


def response_error_messages(response: ApiResponse) -> List[str]:
    return [error.message for error in response.errors]
