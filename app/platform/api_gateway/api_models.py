from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class ApiEndpoint:
    endpoint_id: str
    method: str
    path: str
    domain: str
    version: str
    description: str


@dataclass(frozen=True)
class ApiError:
    code: str
    message: str


@dataclass(frozen=True)
class ApiResponse:
    success: bool
    version: str
    data: Dict[str, object]
    errors: List[ApiError]
