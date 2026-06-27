from __future__ import annotations

from typing import Dict

from app.platform.plugins.plugin import PlatformPlugin


def plugin_registry() -> Dict[str, PlatformPlugin]:
    core = PlatformPlugin(
        plugin_id="platform_core_plugin",
        provider="platform_core",
        capabilities=["runtime", "events", "self_healing"],
        status="active",
        version="1.0.0",
    )
    return {core.plugin_id: core}


def active_plugins() -> Dict[str, PlatformPlugin]:
    return {
        plugin_id: plugin
        for plugin_id, plugin in plugin_registry().items()
        if plugin.status == "active"
    }
