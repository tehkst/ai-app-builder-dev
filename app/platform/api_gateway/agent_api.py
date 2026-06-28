from __future__ import annotations

from app.platform.api_gateway.api_response import ok_response


def agent_summary():
    return ok_response({"domain": "agents", "status": "available"})
