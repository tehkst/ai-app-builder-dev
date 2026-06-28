from __future__ import annotations

from typing import List

from app.platform.events.event import PlatformEvent
from app.platform.events.event_metrics import event_metrics
from app.platform.operations.operations_models import DashboardPanel


def event_panel(events: List[PlatformEvent]) -> DashboardPanel:
    metrics = event_metrics(events)
    return DashboardPanel(
        panel_id="platform_events",
        title="Platform Events",
        status="active",
        value=str(metrics.get("event_count", 0)),
    )
