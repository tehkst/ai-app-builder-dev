from __future__ import annotations

from typing import List

from app.platform.operations.operations_models import DashboardPanel
from app.platform.webconsole.console_models import ConsoleCard, ConsoleView


def operations_view(panels: List[DashboardPanel]) -> ConsoleView:
    cards = [
        ConsoleCard(
            card_id=panel.panel_id,
            title=panel.title,
            value=panel.value,
            status=panel.status,
            metadata={},
        )
        for panel in panels
    ]
    return ConsoleView("operations_view", "Operations", cards)
