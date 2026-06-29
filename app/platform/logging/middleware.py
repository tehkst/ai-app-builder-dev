from __future__ import annotations

import logging
import time
from typing import Callable

from fastapi import Request, Response

from app.platform.logging import new_request_id

logger = logging.getLogger("ai_factory.request")


async def request_logging_middleware(request: Request, call_next: Callable) -> Response:
    request_id = request.headers.get("x-request-id") or new_request_id()
    started = time.time()
    response = await call_next(request)
    duration_ms = int((time.time() - started) * 1000)
    response.headers["x-request-id"] = request_id
    logger.info(
        "request completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response
