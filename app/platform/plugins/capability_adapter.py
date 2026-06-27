from __future__ import annotations

from typing import List

from app.platform.plugins.plugin_registry import active_plugins


def matching_plugins(capability: str) -> List[str]:
    result: List[str] = []
    for plugin in active_plugins().values():
        if capability in plugin.capabilities:
            result.append(plugin.plugin_id)
    return result


def has_capability(capability: str) -> bool:
    return len(matching_plugins(capability)) > 0
