from __future__ import annotations

from typing import Dict

from app.platform.plugins.plugin import PlatformPlugin
from app.platform.webconsole.console_models import ConsoleCard, ConsoleView


def plugin_view(plugins: Dict[str, PlatformPlugin]) -> ConsoleView:
    active_count = len([plugin for plugin in plugins.values() if plugin.status == "active"])
    cards = [
        ConsoleCard("plugin_count", "Plugins", str(len(plugins)), "active", {}),
        ConsoleCard("active_plugins", "Active Plugins", str(active_count), "healthy", {}),
    ]
    return ConsoleView("plugin_view", "Plugins", cards)
