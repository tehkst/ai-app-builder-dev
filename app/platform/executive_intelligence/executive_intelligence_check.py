from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

from app.platform.company_intelligence.service import build_company_intelligence_snapshot
from app.platform.executive_intelligence.service import PRIMARY_REPOSITORY, build_executive_intelligence_briefing
from app.platform.mission_control.service import build_mission_control_summary


def _repo(sha: str) -> Dict[str, Any]:
    return {"repository": PRIMARY_REPOSITORY, "branch": "main", "head_sha": sha, "latest_commit_timestamp": "2026-07-18T00:00:00+00:00", "working_tree_status": ""}


def _mission(stage: str) -> Dict[str, Any]:
    mission = {"mission_id": "MISSION-LIVE", "title": "Live mission", "status": stage, "current_stage": stage, "next_recommended_action": "Review the current mission transition."}
    return {"status": "mission-pipeline-observer-ready", "active_missions": [mission], "summary": {"active": 1, "blocked": 0}}


def _sources(sha: str = "sha-one", stage: str = "planning") -> Dict[str, Any]:
    return {
        "repository": lambda: _repo(sha),
        "missions": lambda: _mission(stage),
        "capabilities": lambda: {"status": "capability-intelligence-ready", "record_count": 20},
        "github": lambda: {"status": "observed", "open_prs": [{"number": 401, "title": "Live PR"}], "checks_summary": {"overall": "passing", "total": 3}, "latest_merge": {"number": 400, "merge_commit_sha": "merge-sha"}},
        "deployment": lambda: {"status": "observed", "revision": "revision-42", "traffic": [{"revisionName": "revision-42", "percent": 100}]},
        "verification": lambda: {"status": "verification-complete", "overall_result": "pass"},
        "health": lambda: {"status": "healthy", "components": []},
        "sprint": lambda: {"status": "active", "sprint_id": "SPRINT-2", "progress": {"completed": 2, "total": 5}},
        "release": lambda: {"status": "release-observed", "stage": "production", "revision": "revision-42"},
    }


def main() -> None:
    first = build_executive_intelligence_briefing(_sources("sha-one", "planning"))
    second = build_executive_intelligence_briefing(_sources("sha-two", "change_set_ready"))
    assert first["head_sha"]["value"] == "sha-one" and second["head_sha"]["value"] == "sha-two"
    assert first["mission_stage"]["value"] == "planning" and second["mission_stage"]["value"] == "change_set_ready"
    assert second["open_prs"]["value"][0]["number"] == 401
    assert second["ci_check_status"]["value"]["overall"] == "passing"
    assert second["deployed_revision"]["value"] == "revision-42"
    assert second["deployment_traffic"]["value"][0]["percent"] == 100
    assert second["production_verification"]["value"]["overall_result"] == "pass"
    assert second["project_progress"]["status"] == "unknown"
    assert "authoritative project-wide gate" in second["project_progress"]["unknown_reason"]
    assert all(second[key]["source"] for key in ("head_sha", "active_mission", "open_prs", "deployed_revision", "platform_health"))
    assert second["governance"]["read_only"] is True and second["governance"]["github_mutation"] is False and second["governance"]["secrets_exposed"] is False

    failing = _sources()
    failing["github"] = lambda: (_ for _ in ()).throw(RuntimeError("offline"))
    isolated = build_executive_intelligence_briefing(failing)
    assert isolated["status"] == "executive-state-ready"
    assert isolated["open_prs"]["status"] == "unknown" and "RuntimeError" in isolated["open_prs"]["unknown_reason"]
    assert isolated["blockers"]["status"] == "unknown" and "github" in isolated["blockers"]["unknown_reason"]
    assert isolated["head_sha"]["value"] == "sha-one"

    no_evidence = build_executive_intelligence_briefing({name: (lambda: {"status": "unknown", "unknown_reason": "not available"}) for name in _sources()})
    assert no_evidence["current_sprint"]["status"] == "unknown"
    assert no_evidence["release_stage"]["status"] == "unknown"
    assert no_evidence["production_verification"]["status"] == "unknown"

    with patch("app.platform.executive_intelligence.service.build_executive_intelligence_briefing", return_value=second):
        company = build_company_intelligence_snapshot()
    assert company["source"] == "executive_intelligence" and company["authoritative"] is False and company["raw_status"] is second

    unknown_health = dict(second)
    unknown_health["platform_health"] = {
        "status": "unknown", "value": None, "unknown_reason": "health source unavailable"
    }
    with patch("app.platform.executive_intelligence.service.build_executive_intelligence_briefing", return_value=unknown_health):
        mission_control = build_mission_control_summary()
    assert mission_control.health == "unknown"

    context_source = Path("app/platform/board_room/context_retriever.py").read_text(encoding="utf-8")
    decision_source = Path("app/platform/board_room/executive_decision_engine.py").read_text(encoding="utf-8")
    dashboard_source = Path("app/platform/ui/executive_state_script.py").read_text(encoding="utf-8")
    legacy_founder_source = Path("app/platform/ui/founder_experience.py").read_text(encoding="utf-8")
    workforce_source = Path("app/platform/ai_workforce/service.py").read_text(encoding="utf-8")
    executive_sources = "\n".join(Path(path).read_text(encoding="utf-8") for path in ("app/platform/executive_intelligence/service.py", "app/platform/company_intelligence/service.py", "app/platform/executive_office/service.py"))
    assert "build_executive_intelligence_briefing" in context_source and "build_company_intelligence_snapshot" not in context_source
    assert "estimated_completion_percent" not in decision_source
    assert "/mission-control/executive-intelligence/briefing" in dashboard_source
    assert "refreshExecutiveState" in dashboard_source and "No authoritative live evidence" in legacy_founder_source
    assert all(value not in legacy_founder_source for value in ("$128,430", "$162,920", "72%", "41%", "$68,340"))
    assert '_kpi("Company health", "healthy", "healthy")' not in workforce_source
    assert "build_executive_intelligence_briefing" in workforce_source
    assert "estimated_completion_percent" not in executive_sources and '"estimated_completion_percent"' not in executive_sources
    assert '"68"' not in executive_sources
    print("Executive Intelligence canonical live-state checks passed")


if __name__ == "__main__":
    main()
