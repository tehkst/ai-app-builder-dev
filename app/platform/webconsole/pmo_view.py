from __future__ import annotations

from app.platform.webconsole.console_models import ConsoleCard, ConsoleView


def pmo_view(epic_count: int, feature_count: int, task_count: int) -> ConsoleView:
    cards = [
        ConsoleCard("pmo_epics", "Epics", str(epic_count), "active", {}),
        ConsoleCard("pmo_features", "Features", str(feature_count), "active", {}),
        ConsoleCard("pmo_tasks", "Tasks", str(task_count), "active", {}),
    ]
    return ConsoleView("pmo_view", "PMO", cards)
