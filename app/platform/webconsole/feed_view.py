from __future__ import annotations

from app.platform.feed.feed_models import FeedContext
from app.platform.feed.feed_store import summarize_feed
from app.platform.webconsole.console_models import ConsoleCard, ConsoleView


def admin_feed_view(context: FeedContext, tenant_id: str) -> ConsoleView:
    summary = summarize_feed(context.events, tenant_id)
    return ConsoleView(
        view_id="admin_feed",
        title="Activity",
        cards=[
            ConsoleCard("events", "Events", str(summary.event_count), "healthy", {}),
            ConsoleCard("tenant", "Tenant Events", str(summary.tenant_event_count), "healthy", {}),
            ConsoleCard("high", "High", str(summary.high_count), "healthy", {}),
            ConsoleCard("lifecycle", "Lifecycle", str(summary.lifecycle_count), "healthy", {}),
            ConsoleCard("catalog", "Catalog", str(summary.catalog_count), "healthy", {}),
            ConsoleCard("tasks", "Tasks", str(summary.task_count), "healthy", {}),
        ],
    )
