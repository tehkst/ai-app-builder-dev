from __future__ import annotations

from app.platform.api_gateway.api_response import ok_response
from app.platform.plugins.plugin_registry import plugin_registry


def plugin_summary():
    return ok_response({"domain": "plugins", "plugin_count": len(plugin_registry())})
