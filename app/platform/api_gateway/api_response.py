from __future__ import annotations

from typing import Dict, List

from app.platform.api_gateway.api_models import ApiError, ApiResponse


def ok_response(data: Dict[str, object], version: str = "v1") -> ApiResponse:
    return ApiResponse(success=True, version=version, data=data, errors=[])


def error_response(code: str, message: str, version: str = "v1") -> ApiResponse:
    return ApiResponse(
        success=False,
        version=version,
        data={},
        errors=[ApiError(code=code, message=message)],
    )


def response_error_messages(response: ApiResponse) -> List[str]:
    return [error.message for error in response.errors]
