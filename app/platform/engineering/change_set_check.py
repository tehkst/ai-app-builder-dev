from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock, patch

import app.platform.execution.service as execution_service
from app.platform.engineering.change_set_service import REPO_ROOT, generate_executable_change_set
from app.platform.execution.orchestrator import execute_authorized_engineering_workflow
from app.platform.github_execution.approved_executor import APPROVAL_PHRASE
from app.platform.journey_inspection.service import inspect_mission_journey


MISSION_ID = "MISSION-ENGINEERING-01"
UPDATE_PATH = "app/platform/engineering/__init__.py"
CREATE_PATH = "app/platform/engineering/generated_change_example.py"


def _mission(*, plan: bool = True, handoff: bool = True, plan_id: str = "PLAN-1") -> dict:
    evidence = {"mission_id": MISSION_ID, "founder_request": "Add a small, repository-grounded engineering example."}
    if plan:
        evidence["planning_result"] = {"status": "engineering-plan-created", "plan": {"plan_id": plan_id, "mission_id": MISSION_ID, "founder_request": evidence["founder_request"], "affected_files": [UPDATE_PATH, CREATE_PATH], "validation_plan": ["python3 -m compileall app/platform/engineering"]}}
    if handoff:
        evidence["engineering_handoff"] = {"status": "engineering-breakdown-created", "breakdown_id": "EM-1", "mission_id": MISSION_ID, "founder_request": evidence["founder_request"], "validation_plan": ["python3 -m compileall app/platform/engineering"]}
    return evidence


def _model_output(update_content: str, **overrides: object) -> str:
    value = {
        "mission_id": MISSION_ID,
        "files": [
            {"path": UPDATE_PATH, "operation": "update", "content": update_content, "rationale": "Expose the approved engineering marker using the existing package convention.", "source_evidence": [UPDATE_PATH], "confidence": "high"},
            {"path": CREATE_PATH, "operation": "create", "content": "MISSION_MARKER = 'engineering-01'\n", "rationale": "Create the narrowly approved mission module.", "source_evidence": [UPDATE_PATH], "confidence": "medium"},
        ],
        "assumptions": ["The new marker is intentionally internal."],
        "risks": ["A package export could affect import behavior."],
    }
    value.update(overrides)
    return json.dumps(value)


def _invoke(output: str) -> dict:
    return {"status": "completed", "provider": "openai", "model": "test-model", "output_text": output}


def main() -> None:
    original = (REPO_ROOT / UPDATE_PATH).read_text(encoding="utf-8")
    created_target = REPO_ROOT / CREATE_PATH
    assert not created_target.exists()

    assert generate_executable_change_set({"mission_id": "EXEC-UNKNOWN", "mission_evidence": {}})["change_set_status"] == "blocked"
    assert "plan" in generate_executable_change_set({"mission_id": MISSION_ID, "mission_evidence": _mission(plan=False)})["blocked_reason"]
    assert "breakdown" in generate_executable_change_set({"mission_id": MISSION_ID, "mission_evidence": _mission(handoff=False)})["blocked_reason"]
    unsafe = _mission()
    unsafe["planning_result"]["plan"]["affected_files"] = ["../outside.py"]
    assert "Invalid repository path" in generate_executable_change_set({"mission_id": MISSION_ID, "mission_evidence": unsafe})["blocked_reason"]

    execution_service._ACTIVE_MISSION = _mission()
    model = Mock(return_value=_invoke(_model_output(original + "\nENGINEERING_CHANGE_SET = True\n")))
    with patch("app.platform.engineering.change_set_service.invoke_ai", model):
        ready = generate_executable_change_set({"mission_id": MISSION_ID})
        reused = generate_executable_change_set({"mission_id": MISSION_ID})
    assert ready["change_set_status"] == "change_set_ready"
    assert ready["mission_id"] == MISSION_ID
    assert ready["source_plan_id"] == "PLAN-1"
    assert ready["engineering_breakdown_id"] == "EM-1"
    assert {item["operation"] for item in ready["files"]} == {"update", "create"}
    assert all(item.get("content") for item in ready["files"])
    assert ready["validation"]["status"] == "passed"
    assert ready["validation"]["commands"]
    assert reused["reused"] is True and model.call_count == 1
    assert (REPO_ROOT / UPDATE_PATH).read_text(encoding="utf-8") == original
    assert not created_target.exists()

    invalid_files = [
        {"path": UPDATE_PATH, "operation": "update", "content": "def broken(:\n", "rationale": "Update the package for the approved mission behavior.", "source_evidence": [UPDATE_PATH], "confidence": "high"},
        {"path": CREATE_PATH, "operation": "create", "content": "from app.platform.missing_module import VALUE\n", "rationale": "Create the approved mission module using local conventions.", "source_evidence": [UPDATE_PATH], "confidence": "medium"},
    ]
    invalid_output = json.dumps({"mission_id": MISSION_ID, "files": invalid_files, "assumptions": [], "risks": []})
    repaired_output = _model_output(original + "\nENGINEERING_CHANGE_SET_REPAIRED = True\n")
    repair_model = Mock(side_effect=[_invoke(invalid_output), _invoke(repaired_output)])
    with patch("app.platform.engineering.change_set_service.invoke_ai", repair_model):
        repaired = generate_executable_change_set({"mission_id": MISSION_ID, "mission_evidence": _mission(plan_id="PLAN-REPAIR")})
    assert repaired["change_set_status"] == "change_set_ready"
    assert repaired["generation"]["repair_attempt_count"] == 1
    assert repair_model.call_count == 2
    first_attempt = repaired["generation"]["attempts"][0]
    failed_by_name = {item["name"]: item for item in first_attempt["failed_checks"]}
    assert failed_by_name["file_0_python_syntax"]["path"] == UPDATE_PATH
    assert failed_by_name["file_1_local_imports"]["path"] == CREATE_PATH
    assert first_attempt["output_sha256"] and first_attempt["candidate_content_retained"] is False

    failed_repair_model = Mock(side_effect=[_invoke(invalid_output), _invoke(invalid_output)])
    with patch("app.platform.engineering.change_set_service.invoke_ai", failed_repair_model):
        repair_blocked = generate_executable_change_set({"mission_id": MISSION_ID, "mission_evidence": _mission(plan_id="PLAN-REPAIR-BLOCKED")})
    assert repair_blocked["change_set_status"] == "blocked"
    assert repair_blocked["mission_id"] == MISSION_ID
    assert repair_blocked["source_plan_id"] == "PLAN-REPAIR-BLOCKED"
    assert repair_blocked["engineering_breakdown_id"] == "EM-1"
    assert repair_blocked["generation"]["repair_attempt_count"] == 1
    assert failed_repair_model.call_count == 2
    assert repair_blocked["validation"]["remaining_failed_checks"]
    assert repair_blocked["approval_required"] == "none"
    assert repair_blocked["next_action"].startswith("Retry executable change-set generation")
    assert (REPO_ROOT / UPDATE_PATH).read_text(encoding="utf-8") == original
    assert not created_target.exists()

    def rejected(files: object) -> dict:
        evidence = _mission(plan_id="PLAN-INVALID")
        output = json.dumps({"mission_id": MISSION_ID, "files": files, "assumptions": [], "risks": []})
        with patch("app.platform.engineering.change_set_service.invoke_ai", return_value=_invoke(output)):
            return generate_executable_change_set({"mission_id": MISSION_ID, "mission_evidence": evidence})

    def failed_names(result: dict) -> set[str]:
        return {item["name"] for item in result["validation"]["remaining_failed_checks"]}

    vague = [{"path": UPDATE_PATH, "operation": "update", "content": "# TODO implement here\n", "rationale": "Change it.", "source_evidence": [UPDATE_PATH], "confidence": "low"}]
    duplicate = json.loads(_model_output(original + "\nVALUE = 2\n"))["files"]
    duplicate.append(dict(duplicate[0]))
    invalid_path = [{"path": "../escape.py", "operation": "create", "content": "VALUE = 1\n", "rationale": "Escape.", "source_evidence": [UPDATE_PATH], "confidence": "low"}]
    unchanged = [{"path": UPDATE_PATH, "operation": "update", "content": original, "rationale": "Preserve the approved target while testing unchanged content.", "source_evidence": [UPDATE_PATH], "confidence": "high"}]
    wrong_operation = [{"path": UPDATE_PATH, "operation": "create", "content": original + "\nVALUE = 3\n", "rationale": "Update the approved target with the requested behavior.", "source_evidence": [UPDATE_PATH], "confidence": "high"}]
    invalid_evidence = [{"path": CREATE_PATH, "operation": "create", "content": "VALUE = 1\n", "rationale": "Create the approved target with complete content.", "source_evidence": ["not/inspected.py"], "confidence": "unknown"}]
    assert {"file_0_content", "file_0_rationale"}.issubset(failed_names(rejected(vague)))
    assert "file_2_unique" in failed_names(rejected(duplicate))
    assert "file_0_path" in failed_names(rejected(invalid_path))
    assert "file_0_changed" in failed_names(rejected(unchanged))
    assert "file_0_operation" in failed_names(rejected(wrong_operation))
    assert {"file_0_evidence", "file_0_confidence"}.issubset(failed_names(rejected(invalid_evidence)))
    assert "files_schema" in failed_names(rejected({}))
    wrong_identity = json.loads(_model_output(original + "\nVALUE = 4\n"))
    wrong_identity["mission_id"] = "MISSION-WRONG"
    with patch("app.platform.engineering.change_set_service.invoke_ai", return_value=_invoke(json.dumps(wrong_identity))):
        identity_blocked = generate_executable_change_set({"mission_id": MISSION_ID, "mission_evidence": _mission(plan_id="PLAN-IDENTITY")})
    assert "mission_identity" in failed_names(identity_blocked)
    with patch("app.platform.engineering.change_set_service.invoke_ai", return_value=_invoke("not-json")):
        invalid_ai = generate_executable_change_set({"mission_id": MISSION_ID, "mission_evidence": _mission(plan_id="PLAN-BAD-AI")})
    assert invalid_ai["change_set_status"] == "blocked"
    assert "structured JSON" in invalid_ai["blocked_reason"]
    assert invalid_ai["generation"]["attempts"][0]["failed_checks"][0]["name"] == "json_parse"

    journey_ready = inspect_mission_journey(MISSION_ID)
    assert journey_ready["engineering_change_set"]["status"] == "ready"
    assert journey_ready["engineering_change_set"]["repository_execution_complete"] is False
    assert next(item for item in journey_ready["stages"] if item["stage_id"] == "code_changes")["status"] != "verified"

    github = Mock(return_value={"status": "pull-request-created", "mission_id": MISSION_ID, "branch_name": f"mission/{MISSION_ID}", "commit": "commit123", "files_changed": [UPDATE_PATH, CREATE_PATH], "pull_request_number": 501, "pull_request_url": "https://github.com/tehkst/ai-app-builder-dev/pull/501"})
    lifecycle = {"status": "pr-status-ready", "state": "open", "mission_id": MISSION_ID, "mission_resolution_status": "resolved", "pr_number": 501}
    with patch("app.platform.execution.orchestrator.validate_code_proposal", return_value={"status": "validated"}), patch("app.platform.execution.orchestrator.execute_approved_github_execution", github), patch("app.platform.execution.orchestrator.get_github_pr_status", return_value=lifecycle):
        workflow = execute_authorized_engineering_workflow({"token": "founder", "mission_id": MISSION_ID, "live_execution": True, "approval_phrase": APPROVAL_PHRASE})
    assert workflow["workflow_status"] == "pull-request-created-and-observed"
    consumed = github.call_args.args[0]["file_changes"]
    assert consumed == ready["files"]
    assert all(workflow["governance"][key] is False for key in ("merge", "deployment", "traffic_shift", "rollback"))
    print("mission plan to executable change set ok")


if __name__ == "__main__":
    main()
