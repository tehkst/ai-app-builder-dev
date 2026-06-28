from __future__ import annotations

from typing import Iterable, List

from app.platform.feed.feed_models import FeedEvent, FeedSummary


def make_event(event_id: str, tenant_id: str, source: str, actor: str, action: str, target: str, severity: str, created_at: str) -> FeedEvent:
    return FeedEvent(event_id, tenant_id, source, actor, action, target, severity, created_at)


def events_for_tenant(events: Iterable[FeedEvent], tenant_id: str) -> List[FeedEvent]:
    return [event for event in events if event.tenant_id == tenant_id]


def events_for_source(events: Iterable[FeedEvent], source: str) -> List[FeedEvent]:
    return [event for event in events if event.source == source]


def summarize_feed(events: Iterable[FeedEvent], tenant_id: str) -> FeedSummary:
    event_list = list(events)
    tenant_events = events_for_tenant(event_list, tenant_id)
    return FeedSummary(
        event_count=len(event_list),
        tenant_event_count=len(tenant_events),
        high_count=len([event for event in tenant_events if event.severity == "high"]),
        lifecycle_count=len([event for event in tenant_events if event.source == "lifecycle"]),
        catalog_count=len([event for event in tenant_events if event.source == "catalog"]),
        task_count=len([event for event in tenant_events if event.source == "task"]),
    )


def latest_events(events: Iterable[FeedEvent], limit: int) -> List[FeedEvent]:
    return sorted(list(events), key=lambda event: event.created_at, reverse=True)[:limit]
