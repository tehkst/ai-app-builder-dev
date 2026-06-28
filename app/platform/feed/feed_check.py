from __future__ import annotations

from app.platform.feed.feed_flow import run_demo_feed
from app.platform.feed.feed_store import events_for_source, events_for_tenant, latest_events, summarize_feed


def main() -> None:
    data = run_demo_feed()
    assert len(data.events) == 4, data

    tenant_events = events_for_tenant(data.events, "tenant_platform")
    assert len(tenant_events) == 3, tenant_events
    assert len(events_for_tenant(data.events, "missing")) == 0

    assert len(events_for_source(data.events, "task")) == 2
    assert latest_events(data.events, 2)[0].event_id == "event_other"

    summary = summarize_feed(data.events, "tenant_platform")
    assert summary.event_count == 4, summary
    assert summary.tenant_event_count == 3, summary
    assert summary.high_count == 1, summary
    assert summary.lifecycle_count == 1, summary
    assert summary.catalog_count == 1, summary
    assert summary.task_count == 1, summary

    print("FEED CHECK PASSED")


if __name__ == "__main__":
    main()
