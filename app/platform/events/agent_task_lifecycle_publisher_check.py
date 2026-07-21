from __future__ import annotations

from typing import List

from app.platform.events.agent_task_lifecycle_publisher import publish_agent_task_lifecycle
from app.platform.events.event_sink import reset_event_sink, set_event_sink


class RecordingSink:
    def __init__(self) -> None:
        self.events: List[object] = []

    def emit(self, event: object) -> None:
        self.events.append(event)


def main() -> None:
    sink = RecordingSink()
    set_event_sink(sink)
    try:
        task = {
            "task_id": "TASK-123",
            "task_type": "approved_mission_stage",
            "parent_task_id": "MISSION-RUN-123",
            "assigned_agent": "worker-1",
            "attempts": 1,
            "max_attempts": 3,
            "input_payload": {"mission_id": "MISSION-123"},
        }
        publish_agent_task_lifecycle(task, lifecycle_status="claimed", assigned_agent="worker-1")
        publish_agent_task_lifecycle(task, lifecycle_status="completed", assigned_agent="planning_agent", result={"success": True})
        publish_agent_task_lifecycle({**task, "task_type": "unrelated"}, lifecycle_status="completed")

        assert len(sink.events) == 2
        claimed, completed = sink.events
        assert claimed.event_type == "agent_task.claimed"
        assert completed.event_type == "agent_task.completed"
        assert claimed.source_authority == "PlatformAgentTask"
        assert claimed.aggregate_id == "MISSION-RUN-123"
        assert claimed.payload["mission_id"] == "MISSION-123"
        assert claimed.metadata["authoritative"] is False
        assert "agent-task:TASK-123" in claimed.evidence_references
        assert completed.idempotency_key == "ORG-AGENT-TASK-TASK-123-completed"
        assert completed.payload["success"] is True
    finally:
        reset_event_sink()

    print("agent task lifecycle publisher contract: PASS")


if __name__ == "__main__":
    main()
