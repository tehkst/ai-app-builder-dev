from __future__ import annotations

from typing import List

from app.platform.runtime.job import RuntimeJob
from app.platform.runtime.worker import RuntimeWorker
from app.platform.saas_portal.portal_models import PortalCard, PortalView


def portal_runtime_view(jobs: List[RuntimeJob], workers: List[RuntimeWorker]) -> PortalView:
    cards = [
        PortalCard("customer_runtime_jobs", "Runtime Jobs", str(len(jobs)), "active", {}),
        PortalCard("customer_runtime_workers", "Runtime Workers", str(len(workers)), "active", {}),
    ]
    return PortalView("runtime_view", "Runtime", cards)
