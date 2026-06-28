from __future__ import annotations

from typing import List

from app.platform.runtime.job import RuntimeJob
from app.platform.runtime.worker import RuntimeWorker
from app.platform.webconsole.console_models import ConsoleCard, ConsoleView


def runtime_view(jobs: List[RuntimeJob], workers: List[RuntimeWorker]) -> ConsoleView:
    cards = [
        ConsoleCard("runtime_jobs", "Runtime Jobs", str(len(jobs)), "active", {}),
        ConsoleCard("runtime_workers", "Runtime Workers", str(len(workers)), "active", {}),
    ]
    return ConsoleView("runtime_view", "Runtime", cards)
