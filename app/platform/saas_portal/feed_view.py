from __future__ import annotations

from app.platform.feed.feed_models import FeedContext
from app.platform.feed.feed_store import summarize_feed
from app.platform.saas_portal.portal_models import PortalCard, PortalView


def portal_feed_view(context: FeedContext, tenant_id: str) -> PortalView:
    summary = summarize_feed(context.events, tenant_id)
    return PortalView(
        view_id="portal_feed",
        title="Activity",
        cards=[
            PortalCard("events", "Events", str(summary.tenant_event_count), "healthy", {}),
            PortalCard("high", "High", str(summary.high_count), "healthy", {}),
            PortalCard("tasks", "Tasks", str(summary.task_count), "healthy", {}),
        ],
    )
