from datetime import datetime, timezone

from app.platform.events import build_organizational_event, emit_organizational_event, reset_event_sink, set_event_sink


class _RecordingSink:
    def __init__(self) -> None:
        self.events = []

    def emit(self, event) -> None:
        self.events.append(event)


class _FailingSink:
    def emit(self, event) -> None:
        raise RuntimeError("expected sink failure")


def run_check() -> None:
    occurred_at = datetime(2026, 7, 21, 8, 0, tzinfo=timezone.utc)
    first = build_organizational_event(
        "mission.workflow-created",
        source="mission-runtime",
        source_authority="PlatformWorkflowRun",
        aggregate_type="mission",
        aggregate_id="MISSION-CHECK-001",
        evidence_references=("workflow:WF-CHECK-001",),
        payload={"workflow_run_id": "WF-CHECK-001"},
        occurred_at=occurred_at,
    )
    second = build_organizational_event(
        "mission.workflow-created",
        source="mission-runtime",
        source_authority="PlatformWorkflowRun",
        aggregate_type="mission",
        aggregate_id="MISSION-CHECK-001",
        evidence_references=("workflow:WF-CHECK-001",),
        payload={"workflow_run_id": "WF-CHECK-001"},
        occurred_at=occurred_at,
    )

    assert first.schema_version == "organizational-event-v1"
    assert first.idempotency_key == second.idempotency_key
    assert first.event_id != second.event_id
    assert first.source_authority == "PlatformWorkflowRun"
    assert first.as_dict()["evidence_references"] == ["workflow:WF-CHECK-001"]

    recorder = _RecordingSink()
    set_event_sink(recorder)
    emit_organizational_event(first)
    assert recorder.events == [first]

    set_event_sink(_FailingSink())
    emit_organizational_event(first)
    reset_event_sink()


if __name__ == "__main__":
    run_check()
    print("governed organizational event contract: PASS")
