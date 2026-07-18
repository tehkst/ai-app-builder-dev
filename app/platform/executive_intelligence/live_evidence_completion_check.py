import os
from tempfile import TemporaryDirectory
from unittest.mock import patch
from unittest.mock import Mock

from app.platform.executive_intelligence.operational_authority import GATE_NAMES, project_gates
from app.platform.executive_intelligence.service import _repository_state, build_executive_intelligence_briefing
from app.platform.github_execution.pr_lifecycle import _github_get


def main() -> None:
    mission = {
        "active_mission": {"value": {"mission_id": "MISSION-LIVE"}},
        "mission_stage": {"value": "change_set_ready"},
    }
    github = {
        "open_prs": {"value": [{"number": 394}]},
        "latest_merge": {"value": {"number": 393}},
    }
    gates = project_gates(mission, github, {"status": "release-observed", "active_revision": "revision-1"}, {"status": "verification-complete", "overall_result": "pass"})
    assert tuple(item["name"] for item in gates["gates"]) == GATE_NAMES
    assert gates["percentage"] == 100.0 and gates["complete"] is True

    with TemporaryDirectory() as directory:
        with patch("app.platform.executive_intelligence.service.REPO_ROOT", directory):
            with patch.dict(os.environ, {"SOURCE_BRANCH": "main", "SOURCE_COMMIT_SHA": "abc123", "SOURCE_COMMIT_TIMESTAMP": "2026-07-18T00:00:00+00:00"}, clear=False):
                repository = _repository_state()
    assert repository["branch"] == "main"
    assert repository["head_sha"] == "abc123"
    assert repository["working_tree_status"] == "not-applicable-immutable-deployment"

    unauthorized = Mock(status_code=401)
    success = Mock(status_code=200)
    success.json.return_value = {"default_branch": "main"}
    with patch("app.platform.github_execution.pr_lifecycle.requests.get", side_effect=[unauthorized, success]) as github_read:
        github_repository = _github_get("", "expired-token")
    assert github_repository["default_branch"] == "main"
    assert "Authorization" in github_read.call_args_list[0].kwargs["headers"]
    assert "Authorization" not in github_read.call_args_list[1].kwargs["headers"]

    sources = {
        "repository": lambda: repository,
        "missions": lambda: {"active_missions": [{"mission_id": "MISSION-LIVE", "current_stage": "change_set_ready"}]},
        "capabilities": lambda: {"status": "ready"},
        "github": lambda: {"status": "observed", "branch": "main", "head_sha": "abc123", "open_prs": [], "checks_summary": {"overall": "not-found", "total": 0}, "latest_merge": None, "workflow_status": []},
        "deployment": lambda: {"status": "observed", "revision": "revision-1", "traffic": [{"revision": "revision-1", "percent": 100}]},
        "verification": lambda: {"status": "verification-complete", "overall_result": "pass"},
        "health": lambda: {"status": "healthy"},
        "sprint": lambda: {"status": "active", "sprint_id": "SPRINT-LIVE", "progress": {"completed": 4, "total": 5, "percentage": 80.0}},
        "release": lambda: {"status": "release-observed", "stage": "production", "active_revision": "revision-1"},
    }
    briefing = build_executive_intelligence_briefing(sources)
    assert briefing["current_sprint"]["value"]["sprint_id"] == "SPRINT-LIVE"
    assert briefing["sprint_progress"]["value"]["percentage"] == 80.0
    assert briefing["release_stage"]["value"]["stage"] == "production"
    assert briefing["production_verification"]["value"]["overall_result"] == "pass"
    assert briefing["deployment_traffic"]["status"] == "observed"
    assert briefing["source_evidence"]["github"]["registry_status"] == "available"
    print("Executive Brain live evidence completion checks passed")


if __name__ == "__main__":
    main()
