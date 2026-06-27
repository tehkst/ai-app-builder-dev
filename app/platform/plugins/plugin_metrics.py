from __future__ import annotations

from typing import Dict, List

from app.platform.plugins.plugin import PlatformPlugin


def plugin_metrics(plugins: List[PlatformPlugin]) -> Dict[str, int]:
    active_count = len([plugin for plugin in plugins if plugin.status == "active"])
    paused_count = len([plugin for plugin in plugins if plugin.status == "paused"])
    retired_count = len([plugin for plugin in plugins if plugin.status == "retired"])
    return {
        "plugin_count": len(plugins),
        "active_plugin_count": active_count,
        "paused_plugin_count": paused_count,
        "retired_plugin_count": retired_count,
    }
