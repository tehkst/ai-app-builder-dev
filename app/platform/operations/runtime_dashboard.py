from __future__ import annotations

from typing import List

from app.platform.operations.operations_models import DashboardPanel
from app.platform.runtime.job import RuntimeJob
from app.platform.runtime.worker import RuntimeWorker


def runtime_panel(jobs: List[RuntimeJob], workers: List[RuntimeWorker]) -> DashboardPanel:
    return DashboardPanel(
        panel_id="runtime_activity",
        title="Runtime Activity",
        status="active",
        value=f"{len(jobs)} jobs / {len(workers)} workers",
    )
