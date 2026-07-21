from __future__ import annotations

from unittest.mock import Mock, patch

from app.platform.runtime_stabilization import stabilize_mission_runtime


MISSION_ID = "MISSION-DA587720B8B6"


def _mission(change_set: dict | None = None) -> dict:
    evidence = {
        "mission_id": MISSION_ID,
        "planning_result": {"plan": {"mission_id": MISSION_ID, "plan_id": "PLAN-RUNTIME-01"}},
        "engineering_handoff": {"mission_id": MISSION_ID, "breakdown_id": "BREAKDOWN-RUNTIME-01"},
    }
    if change_set is not None:
        evidence["executable_change_set"] = change_set
    return evidence


def main() -> None:
    missing = stabilize_mission_runtime.__module__
    assert missing == "app.platform.runtime_stabilization"

    with patch(
        "app.platform.runtime_stabilization.get_execution_mission_evidence",
        return_value={},
    ), patch(
        "app.platform.runtime_stabilization.generate_executable_change_set"
    ) as generator:
        blocked = stabilize_mission_runtime(MISSION_ID)
    assert blocked.status == "blocked"
    assert blocked.attempted is False
    assert blocked.retryable is False
    generator.assert_not_called()

    ready_change_set = {
        "mission_id": MISSION_ID,
        "change_set_status": "change_set_ready",
        "source_plan_id": "PLAN-RUNTIME-01",
        "engineering_breakdown_id": "BREAKDOWN-RUNTIME-01",
        "files": [{"path": "app/example.py", "operation": "update", "content": "VALUE = 1\n"}],
    }
    with patch(
        "app.platform.runtime_stabilization.get_execution_mission_evidence",
        return_value=_mission(ready_change_set),
    ), patch(
        "app.platform.runtime_stabilization.generate_executable_change_set"
    ) as generator:
        reused = stabilize_mission_runtime(MISSION_ID)
    assert reused.status == "stable"
    assert reused.change_set_status == "change_set_ready"
    assert reused.attempted is False
    generator.assert_not_called()

    failed_check = {
        "name": "file_0_evidence",
        "reason": "Source evidence is missing.",
        "path": "app/example.py",
    }
    blocked_change_set = {
        "mission_id": MISSION_ID,
        "change_set_status": "blocked",
        "blocked_reason": "The proposed change could not yet be grounded in inspected repository evidence.",
        "next_action": "Retry change-set generation after retrieving the required repository evidence.",
        "validation": {"remaining_failed_checks": [failed_check]},
    }
    recorder = Mock()
    with patch(
        "app.platform.runtime_stabilization.get_execution_mission_evidence",
        return_value=_mission(),
    ), patch(
        "app.platform.runtime_stabilization.generate_executable_change_set",
        return_value=blocked_change_set,
    ) as generator, patch(
        "app.platform.runtime_stabilization.record_execution_mission_evidence",
        recorder,
    ):
        retried = stabilize_mission_runtime(MISSION_ID, provider="configured", model="configured")
    assert retried.status == "blocked"
    assert retried.attempted is True
    assert retried.retryable is True
    assert retried.remaining_failed_checks == (failed_check,)
    generator.assert_called_once()
    recorder.assert_called_once_with(MISSION_ID, "executable_change_set", blocked_change_set)

    valid_change_set = {
        "mission_id": MISSION_ID,
        "change_set_status": "change_set_ready",
        "blocked_reason": None,
        "validation": {"status": "passed", "checks": []},
        "files": [{"path": "app/example.py", "operation": "update", "content": "VALUE = 2\n"}],
    }
    with patch(
        "app.platform.runtime_stabilization.get_execution_mission_evidence",
        return_value=_mission(),
    ), patch(
        "app.platform.runtime_stabilization.generate_executable_change_set",
        return_value=valid_change_set,
    ), patch(
        "app.platform.runtime_stabilization.record_execution_mission_evidence",
    ):
        stable = stabilize_mission_runtime(MISSION_ID)
    assert stable.status == "stable"
    assert stable.change_set_status == "change_set_ready"
    assert stable.attempted is True
    assert stable.retryable is False
    assert stable.remaining_failed_checks == ()
    assert stable.as_dict()["milestone"] == "MC-RUNTIME-01"

    print("mc runtime 01: PASS")


if __name__ == "__main__":
    main()
