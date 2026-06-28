from __future__ import annotations

from app.platform.api_gateway.api_response import ok_response


def pmo_summary():
    return ok_response({"domain": "pmo", "status": "available"})
