from __future__ import annotations

from typing import Dict

from app.platform.webconsole.console_models import ConsoleCard, ConsoleView


def agent_view(agent_count: int, capability_count: int) -> ConsoleView:
    cards = [
        ConsoleCard("agent_count", "Agents", str(agent_count), "active", {}),
        ConsoleCard("agent_capabilities", "Capabilities", str(capability_count), "active", {}),
    ]
    return ConsoleView("agent_view", "Agents", cards)
