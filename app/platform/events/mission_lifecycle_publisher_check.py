from __future__ import annotations

from typing import List

from app.platform.events.event_models import OrganizationalEvent
from app.platform.events.event_sink import reset_event_sink, set_event_sink
from app.platform.events.mission_lifecycle_publisher import publish_persisted_workflow_lifecycle


class CapturingSink:
    def __init__(self) -> None:
        self.events: List[OrganizationalEvent] = []

    def emit(self, event: OrganizationalEvent) -> None:
        self.events.append(event)


def main() -> None:
    sink = CapturingSink()
    set_event_sink(sink)
    try:
        result = {
            "workflow_run_id": "MISSION-RUN-CHECK",
            "workflow_name": "Durable Board Room Mission Run",
            "status": "change_set_ready",
            "plan_status": "change_set_ready",
            "metadata": {
                "mission_id": "MISSION-CHECK",
                "evidence_id": "EVIDENCE-CHECK",
                "validation_record_id": "VALIDATION-CHECK",
                "change_set_id": "CHANGESET-CHECK",
                "evidence_references": ["LEGACY-EVIDENCE-CHECK"],
            },
        }
        publish_persisted_workflow_lifecycle(result)
        publish_persisted_workflow_lifecycle(result)

        assert [event.event_type for event in sink.events] == [
            "mission.workflow_persisted",
            "mission.stage_changed",
            "mission.change_set_verified",
            "mission.workflow_persisted",
            "mission.stage_changed",
            "mission.change_set_verified",
        ]
        first = sink.events[0]
        assert first.source_authority == "PlatformWorkflowRun"
        assert first.aggregate_id == "MISSION-CHECK"
        assert first.metadata["authoritative"] is False
        assert first.evidence_references == (
            "EVIDENCE-CHECK",
            "VALIDATION-CHECK",
            "CHANGESET-CHECK",
            "LEGACY-EVIDENCE-CHECK",
        )
        assert [reference.as_dict() for reference in first.authority_references] == [
            {
                "authority": "PlatformWorkflowRun",
                "entity_id": "MISSION-RUN-CHECK",
                "relationship": "authoritative_source",
            },
            {
                "authority": "PlatformOperationalEvidence",
                "entity_id": "EVIDENCE-CHECK",
                "relationship": "supporting_evidence",
            },
            {
                "authority": "PlatformExecutionEvidence",
                "entity_id": "VALIDATION-CHECK",
                "relationship": "supporting_evidence",
            },
            {
                "authority": "PlatformWorkspaceArtifact",
                "entity_id": "CHANGESET-CHECK",
                "relationship": "supporting_evidence",
            },
        ]
        assert sink.events[0].idempotency_key == sink.events[3].idempotency_key
        assert sink.events[1].idempotency_key == sink.events[4].idempotency_key
        assert sink.events[2].idempotency_key == sink.events[5].idempotency_key

        before = len(sink.events)
        publish_persisted_workflow_lifecycle(
            {
                "workflow_run_id": "OTHER-RUN",
                "workflow_name": "Unrelated Workflow",
                "status": "completed",
                "metadata": {"mission_id": "OTHER"},
            }
        )
        assert len(sink.events) == before
    finally:
        reset_event_sink()

    print("mission lifecycle publisher checks passed")


if __name__ == "__main__":
    main()
