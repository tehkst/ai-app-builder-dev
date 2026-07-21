from __future__ import annotations

from unittest.mock import patch

from app.platform.operating_console.runtime_inspection_service import inspect_runtime


def main() -> None:
    detail = {
        "found": True,
        "workflow_run_id": "MISSION-RUN-CHECK",
        "workflow_name": "Durable Board Room Mission Run",
        "status": "blocked",
        "step_count": 1,
        "steps": [
            {
                "step_id": "mission_run_state",
                "step_run_id": "MISSION-RUN-CHECK-STATE",
                "status": "blocked",
                "handler_result": {
                    "mission_id": "MISSION-CHECK",
                    "change_set": {
                        "change_set_status": "blocked",
                        "blocking_reason": "change_set_validation_failure",
                        "validation": {"status": "failed"},
                    },
                },
                "error": {"classification": "change_set_validation_failure"},
            }
        ],
    }

    with patch(
        "app.platform.operating_console.runtime_inspection_service.require_founder",
        return_value={"authorized": False},
    ):
        blocked = inspect_runtime({"type": "workflow_run", "id": "MISSION-RUN-CHECK"})
    assert blocked == {
        "status": "blocked",
        "authorized": False,
        "reason": "founder_authorization_required",
    }

    with patch(
        "app.platform.operating_console.runtime_inspection_service.require_founder",
        return_value={"authorized": True},
    ), patch(
        "app.platform.operating_console.runtime_inspection_service.get_workflow_run_detail",
        return_value=detail,
    ):
        result = inspect_runtime({
            "token": "founder-session",
            "type": "workflow_run",
            "id": "MISSION-RUN-CHECK",
        })

    assert result["found"] is True
    assert result["workflow_status"] == "blocked"
    assert result["steps"][0]["has_change_set"] is True
    assert result["steps"][0]["handler_keys"] == ["change_set", "mission_id"]
    assert result["steps"][0]["change_set_keys"] == [
        "blocking_reason",
        "change_set_status",
        "validation",
    ]
    assert "founder-session" not in str(result)

    with patch(
        "app.platform.operating_console.runtime_inspection_service.require_founder",
        return_value={"authorized": True},
    ), patch(
        "app.platform.operating_console.runtime_inspection_service.get_workflow_run_detail",
        return_value={"found": False},
    ):
        missing = inspect_runtime({
            "token": "founder-session",
            "type": "workflow_run",
            "id": "MISSION-RUN-MISSING",
        })
    assert missing["status"] == "not_found" and missing["found"] is False

    print("founder runtime workflow inspection ok")


if __name__ == "__main__":
    main()
