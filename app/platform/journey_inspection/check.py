from __future__ import annotations

from copy import deepcopy

from app.platform.board_room.context_retriever import ContextRetriever
from app.platform.journey_inspection.service import inspect_mission_journey


MISSION_ID = "EXEC-JOURNEY01"


def _sources() -> dict:
    return {
        "board_room": {"status": "ready"},
        "founder_approval": {"status": "founder-approval-ready"},
        "execution": {
            "status": "execution-foundation-ready",
            "active_mission": {
                "mission_id": MISSION_ID,
                "founder_request": "Complete one founder journey.",
                "created_at": "2026-07-12T00:00:00+00:00",
            },
        },
        "mission_execution": {"status": "mission-execution-bridge-ready"},
        "founder_workflow": {"status": "founder-workflow-engine-ready"},
        "planning": {"status": "planner-ready"},
        "engineering_manager": {"status": "engineering-manager-ready", "mode": "planning-management-only"},
        "github_execution": {"status": "ready"},
        "github_pr": {"status": "ready"},
        "github_merge": {"status": "ready"},
        "deployment": {"status": "configured"},
        "verification": {"status": "ready"},
    }


def _stage(result: dict, stage_id: str) -> dict:
    return next(item for item in result["stages"] if item["stage_id"] == stage_id)


def _transition(result: dict, left: str, right: str) -> dict:
    return next(
        item
        for item in result["transitions"]
        if item["from_stage"] == left and item["to_stage"] == right
    )


def main() -> None:
    unresolved_sources = _sources()
    unresolved_sources["execution"] = {
        "status": "execution-foundation-ready",
        "active_mission": None,
    }
    unresolved = inspect_mission_journey(source_overrides=unresolved_sources)
    assert unresolved["mission_resolution"]["status"] == "unresolved"
    assert unresolved["journey_health"] == "blocked_for_inspection"
    assert unresolved["first_broken_or_manual_transition"] is None
    assert all(item["status"] == "unknown" for item in unresolved["transitions"])
    assert "canonical mission identity" in unresolved["smallest_next_improvement"]

    not_found = inspect_mission_journey(
        "EXEC-NOTFOUND",
        source_overrides=unresolved_sources,
    )
    assert not_found["mission_resolution"]["status"] == "not_found"
    assert not_found["journey_health"] == "blocked_for_inspection"
    assert not_found["first_broken_or_manual_transition"] is None

    baseline = inspect_mission_journey(MISSION_ID, source_overrides=_sources())
    assert baseline["mission_resolution"]["status"] == "resolved"

    # Capability existence and readiness do not prove mission completion.
    assert _stage(baseline, "planning")["status"] == "ready"
    assert _stage(baseline, "planning")["status"] != "verified"
    assert _stage(baseline, "code_changes")["status"] == "ready"

    # Planning to engineering is a manual handoff without a linked run.
    manual_sources = _sources()
    manual_sources["board_room"] = {
        "status": "ready",
        "mission_id": MISSION_ID,
        "recommendation": {"action": "Proceed"},
    }
    manual_sources["founder_approval"] = {
        "status": "approved",
        "mission_id": MISSION_ID,
        "approval_id": "APPROVAL-1",
    }
    manual_sources["planning"] = {"status": "planning-complete", "mission_id": MISSION_ID, "plan_id": "PLAN-1"}
    manual = inspect_mission_journey(MISSION_ID, source_overrides=manual_sources)
    assert _transition(manual, "Planning", "Engineering execution")["status"] == "manual"
    assert manual["first_broken_or_manual_transition"]["from_stage"] == "Planning"
    assert manual["first_broken_or_manual_transition"]["to_stage"] == "Engineering execution"
    assert manual["first_broken_or_manual_transition"]["status"] == "manual"

    # A shared mission identity verifies a transition.
    linked_sources = deepcopy(manual_sources)
    linked_sources["engineering_manager"] = {
        "status": "completed",
        "mission_id": MISSION_ID,
        "run_id": "RUN-1",
    }
    linked = inspect_mission_journey(MISSION_ID, source_overrides=linked_sources)
    assert _transition(linked, "Planning", "Engineering execution")["status"] == "verified"

    # Mission, PR, deployment, and verification linkages remain explicit.
    assert "Mission creation → Pull request" in baseline["missing_linkages"]
    pr_sources = deepcopy(linked_sources)
    pr_sources["github_execution"] = {
        "status": "completed",
        "mission_id": MISSION_ID,
        "commit_sha": "abc123",
    }
    pr_sources["github_pr"] = {
        "status": "pr-status-ready",
        "mission_id": MISSION_ID,
        "pr_number": 401,
    }
    missing_deployment = inspect_mission_journey(MISSION_ID, source_overrides=pr_sources)
    assert "Pull request → Production deployment" in missing_deployment["missing_linkages"]

    deployment_sources = deepcopy(pr_sources)
    deployment_sources["deployment"] = {
        "status": "deployment-completed",
        "mission_id": MISSION_ID,
        "pr_number": 401,
        "revision_name": "revision-1",
    }
    missing_verification = inspect_mission_journey(MISSION_ID, source_overrides=deployment_sources)
    assert "Production deployment → Verification" in missing_verification["missing_linkages"]

    # The service is explicitly read-only and ContextRetriever preserves structure.
    assert all(value is False for key, value in baseline["governance"].items() if key != "read_only" and key != "stores_state")
    assert baseline["governance"]["read_only"] is True
    assert baseline["governance"]["stores_state"] is False

    retriever = ContextRetriever()
    context = retriever.retrieve(f"Inspect mission {MISSION_ID}")
    journey = context["journey_evidence"]
    assert journey["stages"]
    assert journey["transitions"]
    assert "first_broken_or_manual_transition" in journey
    assert context["sources"]["journey_inspection"] is journey
    print("mission journey inspection ok")


if __name__ == "__main__":
    main()
