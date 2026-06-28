from __future__ import annotations

from app.platform.feed.feed_models import FeedContext
from app.platform.feed.feed_store import make_event


def run_demo_feed() -> FeedContext:
    events = [
        make_event("event_lifecycle", "tenant_platform", "lifecycle", "user_platform_owner", "completed", "AI CRM App", "medium", "2026-06-28T10:00:00Z"),
        make_event("event_catalog", "tenant_platform", "catalog", "user_platform_owner", "activated", "AI CRM Starter", "low", "2026-06-28T10:05:00Z"),
        make_event("event_task", "tenant_platform", "task", "user_platform_owner", "updated", "Prepare CRM app", "high", "2026-06-28T10:10:00Z"),
        make_event("event_other", "other_tenant", "task", "other_user", "updated", "Other task", "low", "2026-06-28T10:15:00Z"),
    ]
    return FeedContext(events=events, metadata={"flow": "feed"})
