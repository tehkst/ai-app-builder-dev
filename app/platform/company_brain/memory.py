from __future__ import annotations

from app.platform.company_brain.event_models import DomainEvent


class CompanyMemory:
    def __init__(self) -> None:
        self._timeline: list[DomainEvent] = []

    def remember(self, event: DomainEvent) -> None:
        self._timeline.append(event)

    def timeline(self) -> list[dict[str, object]]:
        return [event.as_dict() for event in self._timeline]

    def mission_history(self, mission_id: str) -> list[dict[str, object]]:
        return [event.as_dict() for event in self._timeline if event.aggregate_type == "mission" and event.aggregate_id == mission_id]
