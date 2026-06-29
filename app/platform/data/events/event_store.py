from __future__ import annotations

from typing import Dict, List, Optional

from app.platform.data.events.event_models import DataEvent


class EventStore:
    def __init__(self) -> None:
        self._items: Dict[str, DataEvent] = {}

    def append(self, event: DataEvent) -> DataEvent:
        self._items[event.event_id] = event
        return event

    def get(self, event_id: str) -> Optional[DataEvent]:
        return self._items.get(event_id)

    def list_all(self) -> List[DataEvent]:
        return list(self._items.values())

    def list_for_tenant(self, tenant_id: str) -> List[DataEvent]:
        return [event for event in self._items.values() if event.belongs_to(tenant_id)]
