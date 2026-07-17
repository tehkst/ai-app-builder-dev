from __future__ import annotations

from app.platform.company_brain.event_models import DomainEvent
from app.platform.digital_twin.twin_state import TwinState


def apply_domain_event(state: TwinState, event: DomainEvent) -> TwinState:
    payload = dict(event.payload)
    record = {"aggregate_id": event.aggregate_id, "event_type": event.event_type, "updated_at": event.timestamp}
    if event.aggregate_type == "mission":
        state.missions[event.aggregate_id] = {**state.missions.get(event.aggregate_id, {}), **payload, **record}
    elif event.aggregate_type == "workflow":
        state.workflows[event.aggregate_id] = {**state.workflows.get(event.aggregate_id, {}), **payload, **record}
    elif event.aggregate_type == "agent":
        state.agents[event.aggregate_id] = {**state.agents.get(event.aggregate_id, {}), **payload, **record}
    elif event.aggregate_type == "task":
        state.tasks[event.aggregate_id] = {**state.tasks.get(event.aggregate_id, {}), **payload, **record}
    elif event.aggregate_type == "board_room_decision":
        state.board_room_decisions.append({**payload, **record})
    state.last_event_id = event.event_id
    return state
