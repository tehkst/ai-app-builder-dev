from __future__ import annotations

from typing import Optional

from app.platform.plugins.plugin import PlatformPlugin
from app.platform.plugins.plugin_registry import plugin_registry


def load_plugin(plugin_id: str) -> Optional[PlatformPlugin]:
    return plugin_registry().get(plugin_id)


def plugin_loaded(plugin_id: str) -> bool:
    return load_plugin(plugin_id) is not None
