from __future__ import annotations

from copy import deepcopy
from unittest.mock import patch

from app.platform.engineering_manager.service import create_engineering_breakdown
from app.platform.execution.service import create_execution_mission
from app.platform.founder_approval.service import approve_proposal
from app.platform.github_execution.approved_executor import _pr_body_with_mission_marker
from app.platform.github_execution.approved_merge import APPROVAL_PHRASE, execute_github_merge, preview_github_merge
from app.platform.github_execution.pr_lifecycle import resolve_pr_mission_identity
from app.platform.journey_inspection.service import inspect_mission_journey
from app.platform.operating_console.service import _approved_mission_id
from app.platform.pipeline.mission_pipeline import MissionAggregator, build_mission_pipeline_summary
from app.platform.planning.service import generate_engineering_plan


MISSION_ID = "MISSION-123"


def _authorized(_: dict) -> dict:
    return {"authorized": True, "role": "founder"}


def _pr(body: str = "", branch: str = "feature/ui", title: str = "UI polish") -> dict:
    return {
        "number": 42,
        "body": body,
        "title": title,
        "state": "open",
        "merged": False,
        "mergeable": True,
        "html_url": "https://github.com/tehkst/ai-app-builder-dev/pull/42",
        "head": {"ref": branch, "sha": "abc123"},
        "base": {"ref": "main"},
    }


def main() -> None:
    with patch("app.platform.founder_approval.service._write_artifacts", return_value={"mode": "test"}):
        generated = approve_proposal({"proposal_id": "PROP-1"})
        preserved = approve_proposal({"proposal_id": "PROP-2", "mission_id": MISSION_ID})
        provisional = approve_proposal({"proposal_id": "PROP-3", "mission_id": "EXEC-ABC123"})
    assert generated["mission_id"].startswith("MISSION-")
    assert preserved["mission_id"] == MISSION_ID
    assert provisional["mission_id"].startswith("MISSION-") and provisional["mission_id"] != "EXEC-ABC123"
    assert provisional["originating_mission_id"] == "EXEC-ABC123"
    assert _approved_mission_id("EXEC-ABC123", {"mission_id": MISSION_ID}) == MISSION_ID

    with patch("app.platform.execution.service.require_founder", _authorized):
        execution = create_execution_mission({"mission_id": MISSION_ID, "founder_request": "Polish the UI."})
    assert execution["mission"]["mission_id"] == MISSION_ID

    with patch("app.platform.planning.service.require_founder", _authorized):
        planning = generate_engineering_plan({"mission_id": MISSION_ID, "founder_request": "Polish the UI."})
    assert planning["plan"]["mission_id"] == MISSION_ID
    with patch("app.platform.engineering_manager.service.require_founder", _authorized):
        engineering = create_engineering_breakdown({"planner_output": planning})
    assert engineering["mission_id"] == MISSION_ID

    body = _pr_body_with_mission_marker("Approved UI polish", MISSION_ID)
    assert body.endswith(f"Mission-ID: {MISSION_ID}")
    structured = resolve_pr_mission_identity(_pr(body=body))
    assert structured["mission_id"] == MISSION_ID
    assert structured["mission_resolution_source"] == "pr-body-marker"
    branch_fallback = resolve_pr_mission_identity(_pr(branch=f"feature/{MISSION_ID}"))
    assert branch_fallback["mission_id"] == MISSION_ID
    title_fallback = resolve_pr_mission_identity(_pr(title=f"Implement {MISSION_ID}"))
    assert title_fallback["mission_id"] == MISSION_ID
    ambiguous = resolve_pr_mission_identity(_pr(body=f"Mission-ID: {MISSION_ID}", title="Implement MISSION-999"))
    assert ambiguous["mission_id"] is None
    assert ambiguous["mission_resolution_status"] == "ambiguous"
    assert resolve_pr_mission_identity(_pr())["mission_resolution_status"] == "unresolved"

    pr = _pr(body=body)
    with patch.dict("os.environ", {"GITHUB_TOKEN": "secret"}), patch("app.platform.github_execution.approved_merge.require_founder", _authorized), patch("app.platform.github_execution.approved_merge._read_pr_status", return_value=(pr, {"overall": "passing"}, None)):
        preview = preview_github_merge({"token": "founder", "pr_number": 42})
        assert preview["mission_id"] == MISSION_ID
        with patch("app.platform.github_execution.approved_merge._github_put", return_value={"sha": "merge123", "message": "merged"}):
            merged = execute_github_merge({"token": "founder", "pr_number": 42, "merge_method": "squash", "live_execution": True, "approval_phrase": APPROVAL_PHRASE})
    assert merged["mission_id"] == MISSION_ID
    assert merged["merge_commit_sha"] == "merge123"

    with patch("app.platform.pipeline.mission_pipeline.build_execution_summary", return_value={"status": "execution-foundation-ready", "active_mission": None}):
        pipeline = build_mission_pipeline_summary()
        snapshot = MissionAggregator().snapshot()
        synthetic_lookup = MissionAggregator().mission("MISSION-CONTROL-001")
    assert pipeline["summary"]["active"] == 0
    assert pipeline["summary"]["blocked"] == 0
    assert snapshot["missions"][0]["synthetic"] is True
    assert synthetic_lookup is None

    sources = {
        "execution": {"status": "active", "active_mission": {"mission_id": MISSION_ID, "founder_request": "Polish UI", "created_at": "2026-07-12T00:00:00Z"}},
        "board_room": {"status": "ready", "mission_id": MISSION_ID, "recommendation": {"action": "Proceed"}},
        "founder_approval": {"status": "approved", "mission_id": MISSION_ID, "approval_id": "APPR-1"},
        "planning": {"status": "planning-complete", "mission_id": MISSION_ID, "plan_id": "PLAN-1"},
        "engineering_manager": {"status": "completed", "mission_id": MISSION_ID, "run_id": "RUN-1"},
        "github_execution": {"status": "completed", "mission_id": MISSION_ID, "commit_sha": "abc123"},
        "github_pr": {"status": "pr-status-ready", "mission_id": MISSION_ID, "mission_resolution_status": "resolved", "pr_number": 42},
        "github_merge": {"status": "pr-merged", "mission_id": MISSION_ID, "mission_resolution_status": "resolved", "pr_number": 42, "merged": True, "merge_commit_sha": "merge123"},
    }
    journey = inspect_mission_journey(MISSION_ID, source_overrides=deepcopy(sources))
    assert next(stage for stage in journey["stages"] if stage["stage_id"] == "pull_request")["status"] == "verified"
    assert next(stage for stage in journey["stages"] if stage["stage_id"] == "merge")["status"] == "verified"
    through_merge = [stage for stage in journey["stages"] if stage["stage_id"] in {"founder_approval", "mission_creation", "planning", "engineering_execution", "code_changes", "pull_request", "merge"}]
    assert all(stage["status"] == "verified" for stage in through_merge)
    assert preview["founder_approval_required"] is True and merged["founder_approval_required"] is True
    print("canonical mission identity through merge ok")


if __name__ == "__main__":
    main()
