from __future__ import annotations

from app.platform.events.event import PlatformEvent
from app.platform.events.event_types import JOB_COMPLETED, JOB_FAILED, VALIDATION_FAILED
from app.platform.self_healing.anomaly_detector import detect_anomalies, has_anomaly
from app.platform.self_healing.diagnosis_engine import diagnose
from app.platform.self_healing.execution_supervisor import supervise_action
from app.platform.self_healing.health_monitor import health_status, health_summary
from app.platform.self_healing.learning_collector import collect_learning
from app.platform.self_healing.recovery_planner import ROLLBACK, recovery_plan
from app.platform.self_healing.verification_engine import verify_outcome


def main() -> None:
    events = [
        PlatformEvent(
            event_id="heal_1",
            event_type=JOB_FAILED,
            source="runtime",
            payload={"job_id": "job1"},
            created_at="2026-01-01T00:00:00Z",
        ),
        PlatformEvent(
            event_id="heal_2",
            event_type=VALIDATION_FAILED,
            source="validation",
            payload={"check": "runtime"},
            created_at="2026-01-01T00:00:01Z",
        ),
        PlatformEvent(
            event_id="heal_3",
            event_type=JOB_COMPLETED,
            source="runtime",
            payload={"job_id": "job2"},
            created_at="2026-01-01T00:00:02Z",
        ),
    ]

    summary = health_summary(events)
    assert summary["event_count"] == 3, summary
    assert health_status(events) == "healthy"
    assert has_anomaly(events) is True

    anomalies = detect_anomalies(events)
    diagnosis = diagnose(anomalies)
    assert diagnosis == "validation_failure", diagnosis

    plan = recovery_plan(diagnosis)
    assert plan == ROLLBACK, plan

    supervision = supervise_action(plan)
    assert supervision["status"] == "scheduled", supervision

    result = verify_outcome(supervision)
    assert result == "verification_pending", result

    learning = collect_learning([], diagnosis, plan, result)
    assert learning[0]["diagnosis"] == diagnosis, learning

    print("SELF HEALING CHECK PASSED")


if __name__ == "__main__":
    main()
