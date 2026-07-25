from __future__ import annotations

from unittest.mock import patch

from app.platform.organization_console.service import (
    _reporting_quality,
    _runtime_status,
    _task_agent_id,
    preview_skill_change,
    query_organisation,
    query_department,
    query_team,
    query_worker_evidence,
    query_worker,
    build_internal_organisation_context,
    query_skill_history,
    query_skill_version,
)
from app.platform.organization_console.skills import active_skill_diagnostic, inject_operational_skills, read_skill_document, validate_skill_document
from app.platform.ai_workforce.service import build_workforce_summary
from app.platform.ui.founder_dashboard_stable import render_stable_founder_dashboard


def main() -> None:
    assert query_organisation({})["status"] == "unauthorised"
    assert query_worker({"agent_id": "architect_agent"})["status"] == "unauthorised"
    assert query_department({"department_id": "architecture"})["status"] == "unauthorised"
    assert query_team({"team_id": "architecture_core"})["status"] == "unauthorised"
    assert query_worker_evidence({"agent_id": "architect_agent"})["status"] == "unauthorised"

    with patch("app.platform.organization_console.service.require_founder", return_value={"authorized": True}):
        projection = query_organisation({"token": "founder"})
        assert projection["status"] == "ready", projection
        assert projection["authority"]["identity"] == "agent-registry", projection
        assert projection["executive"]["display_name"] == "Jarvis", projection
        assert projection["metrics"]["worker_count"] >= 16, projection
        assert projection["data_quality"]["unknown_department_count"] == 2, projection
        engineering = next(item for item in projection["departments"] if item["department_id"] == "engineering_management")
        assert engineering["head_agent_id"] == "engineering_manager_agent", engineering
        department = query_department({"token": "founder", "department_id": "architecture"})
        assert department["department"]["head_agent_id"] == "architect_agent", department
        team = query_team({"token": "founder", "team_id": "architecture_core"})
        assert team["team"]["lead_agent_id"] == "architect_agent", team
        assert all(worker["workload"]["progress_percentage"] is None for worker in projection["workers"])
        assert all(worker["governance"]["capability_grants_authority"] is False for worker in projection["workers"])
        assert build_internal_organisation_context()["worker_count"] == projection["metrics"]["worker_count"]
        worker = query_worker({"token": "founder", "agent_id": "architect_agent"})["worker"]
        assert worker["skills"]["runtime_source"] is True, worker
        assert worker["skills"]["validation"]["valid"] is True, worker
        preview = preview_skill_change({
            "token": "founder",
            "agent_id": "architect_agent",
            "expected_version": worker["skills"]["version"],
            "content": worker["skills"]["content"] + "\n",
        })
        assert preview["status"] == "valid", preview
        assert preview["github_execution_package"]["file_changes"][0]["path"] == "app/platform/agents/skills/architect_agent/skills.md"
        assert preview["github_execution_package"]["live_execution"] is False
        conflict = preview_skill_change({
            "token": "founder",
            "agent_id": "architect_agent",
            "expected_version": "stale",
            "content": worker["skills"]["content"],
        })
        assert conflict["status"] == "conflict", conflict
        with patch(
            "app.platform.organization_console.service.skill_history",
            return_value={"available": True, "items": [{"version": "abc", "actor": "Founder"}]},
        ):
            skill_history_result = query_skill_history({"token": "founder", "agent_id": "architect_agent"})
            assert skill_history_result["history"]["available"]
            assert skill_history_result["lifecycle"][0]["state"] == "Repository version available"
        with patch(
            "app.platform.organization_console.service.read_skill_version",
            return_value={"available": True, "version": "abc", "content": worker["skills"]["content"]},
        ):
            assert query_skill_version({
                "token": "founder", "agent_id": "architect_agent", "version": "abc",
            })["document"]["available"]

    skill = read_skill_document("architect_agent")
    assert skill["available"] and skill["validation"]["valid"], skill
    assert not validate_skill_document("# Incomplete")["valid"]
    enriched = inject_operational_skills({"input_payload": {"mission_id": "MISSION-1"}}, "architect_agent")
    assert enriched["input_payload"]["operational_skills"]["loaded"] is True, enriched
    diagnostic = active_skill_diagnostic("architect_agent")
    assert diagnostic["load_result"] == "loaded", diagnostic
    assert "content" not in diagnostic, diagnostic

    assert _runtime_status([], []) == "Available"
    assert _runtime_status([{"status": "running"}], []) == "Working"
    assert _runtime_status([{"status": "approval_required"}], [{"status": "approval_required"}]) == "Blocked"
    assert _task_agent_id({
        "assigned_agent": "agent-worker-123",
        "result_payload": {"agent_id": "architect_agent"},
        "input_payload": {},
    }) == "architect_agent"
    assert not any(
        item["type"] in {"invalid_manager_id", "circular_reporting", "duplicate_worker_identity"}
        for item in _reporting_quality(projection["workers"])["issues"]
    )
    workforce = build_workforce_summary()
    assert workforce["authority"] == "organisation-console-v1", workforce
    assert workforce["synthetic_workers"] is False, workforce
    assert not {"exec-001", "eng-001", "launch-001"} & {
        item["employee_id"] for item in workforce["employees"]
    }

    dashboard = render_stable_founder_dashboard()
    assert 'data-section="organisation"' in dashboard
    assert 'id="organisation"' in dashboard
    assert "Organisation chart" in dashboard
    assert "◌ Agents" not in dashboard
    assert "if(name==='agents')name='organisation'" in dashboard
    assert "/mission-control/organisation/query" in dashboard
    assert "/mission-control/organisation/worker/evidence" in dashboard
    assert "data-department-toggle" in dashboard
    assert "data-team-toggle" in dashboard
    assert "bindPan" in dashboard
    assert "Prepare restore" in dashboard
    assert "item.display_name" in dashboard
    assert "localStorage.getItem('mission_control_token')" in dashboard
    assert "progress_percentage||0" not in dashboard
    print("AFOS-017A ORGANISATION CONSOLE CHECK PASSED")


if __name__ == "__main__":
    main()
