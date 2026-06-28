from __future__ import annotations

from app.platform.api_gateway.api_response import ok_response


def learning_summary():
    return ok_response({"domain": "learning", "status": "available"})
