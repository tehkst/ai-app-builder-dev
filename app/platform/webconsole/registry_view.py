from __future__ import annotations

from typing import Dict

from app.platform.registry.registry_models import RegistryResource
from app.platform.webconsole.console_models import ConsoleCard, ConsoleView


def registry_view(registry: Dict[str, RegistryResource]) -> ConsoleView:
    active_count = len([resource for resource in registry.values() if resource.active])
    cards = [
        ConsoleCard("registry_resources", "Registered Resources", str(len(registry)), "active", {}),
        ConsoleCard("registry_active", "Active Resources", str(active_count), "healthy", {}),
    ]
    return ConsoleView("registry_view", "Registry", cards)
