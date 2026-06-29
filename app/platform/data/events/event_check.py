from __future__ import annotations

from app.platform.data.events.event_models import DataEvent
from app.platform.data.events.event_store import EventStore


def main() -> None:
    store = EventStore()
    event = DataEvent(
        event_id="event1",
        tenant_id="tenant1",
        kind="record.created",
        source="system",
        target="record1",
    )
    store.append(event)
    assert event.belongs_to("tenant1"), event
    assert store.get("event1") == event
    assert len(store.list_all()) == 1
    assert len(store.list_for_tenant("tenant1")) == 1
    assert len(store.list_for_tenant("tenant2")) == 0
    print("EVENT CHECK PASSED")


if __name__ == "__main__":
    main()
