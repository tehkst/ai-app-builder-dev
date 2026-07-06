from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.platform.services.board_room_orchestrator import run_executive_orchestration
from app.platform.services.sprint_engine import create_autonomous_sprint
from app.platform.services.software_factory_planner import create_software_factory_plan
from app.platform.services.engineering_manager import create_engineering_spec
from app.platform.services.senior_software_engineer import create_implementation_package
from app.platform.services.code_executor import create_code_execution_plan
from app.platform.services.repository_executor_gateway import create_repository_executor_approval_gateway
from app.platform.services.pr_handoff_executor import create_pr_handoff
from app.platform.services.runtime_repository_plugin import build_runtime_repository_plugin
from app.platform.services.runtime_pr_creator_plugin import build_runtime_pr_creator_plugin
from app.platform.services.runtime_release_plugin import build_runtime_release_plugin


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(text: str) -> str:
    value = "".join(ch.lower() if ch.isalnum() else "-" for ch in text).strip("-")
    while "--" in value:
        value = value.replace("--", "-")
    return value[:56] or "mission"


def _timeline_event(step: int, stage: str, status: str, summary: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "step": step,
        "stage": stage,
        "status": status,
        "summary": summary,
        "timestamp": _now(),
        "payload": payload or {},
    }


def run_mission_runtime(
    *,
    goal: str,
    requested_by: str = "founder",
    sprint_days: int = 7,
    capacity_points: int = 20,
    db: Optional[Session] = None,
    scope: str = "mission_control",
) -> Dict[str, Any]:
    mission_id = f"mission-{_slug(goal)}"
    timeline: List[Dict[str, Any]] = [
        _timeline_event(1, "intake", "complete", "Mission intake received from founder.", {"goal": goal}),
    ]

    orchestration = run_executive_orchestration(message=goal, db=db, scope=scope)
    timeline.append(_timeline_event(2, "executive_orchestration", "complete", "Executive orchestrator selected agents and produced consensus.", {"intent": orchestration.get("intent")}))

    sprint = create_autonomous_sprint(goal=goal, sprint_days=sprint_days, capacity_points=capacity_points, db=db, scope=scope)
    timeline.append(_timeline_event(3, "sprint_planning", "complete", "Sprint Engine produced backlog and committed stories.", {"committed": len(sprint.get("committed_stories", []))}))

    factory_plan = create_software_factory_plan(goal=goal, db=db, scope=scope)
    timeline.append(_timeline_event(4, "software_factory_planning", "complete", "Software Factory Planner produced epics, features, tasks, and PR sequence.", {"mission_type": factory_plan.get("mission_type")}))

    engineering_spec = create_engineering_spec(goal=goal, db=db, scope=scope)
    timeline.append(_timeline_event(5, "engineering_management", "complete", "Engineering Manager produced architecture and implementation specification.", {"files": len(engineering_spec.get("file_change_map", []))}))

    implementation_package = create_implementation_package(goal=goal, db=db, scope=scope)
    timeline.append(_timeline_event(6, "senior_engineering", "complete", "Senior Software Engineer produced implementation package.", {"patches": len(implementation_package.get("proposed_patches", []))}))

    execution_plan = create_code_execution_plan(goal=goal, db=db, scope=scope)
    timeline.append(_timeline_event(7, "code_execution_plan", "complete", "Code Executor produced governed execution plan.", {"steps": len(execution_plan.get("execution_steps", []))}))

    approval_gateway = create_repository_executor_approval_gateway(goal=goal, requested_by=requested_by, db=db, scope=scope)
    timeline.append(_timeline_event(8, "approval_gateway", "pending_founder_review", "Repository Executor Approval Gateway is ready for founder review.", {"approval_id": approval_gateway.get("approval_request", {}).get("approval_id")}))

    pr_handoff = create_pr_handoff(goal=goal, requested_by=requested_by, db=db, scope=scope)
    timeline.append(_timeline_event(9, "pr_handoff", "ready_for_review", "Branch and PR handoff contract is ready for external review.", {"branch": pr_handoff.get("handoff", {}).get("proposed_branch")}))

    outputs = {
        "orchestration": orchestration,
        "sprint": sprint,
        "factory_plan": factory_plan,
        "engineering_spec": engineering_spec,
        "implementation_package": implementation_package,
        "execution_plan": execution_plan,
        "approval_gateway": approval_gateway,
        "pr_handoff": pr_handoff,
    }
    outputs["repository_package"] = build_runtime_repository_plugin(goal, outputs, requested_by=requested_by)
    timeline.append(_timeline_event(10, "repository_package", outputs["repository_package"].get("status", "review_package_ready"), "BR-EXEC-02 repository package is attached to Mission Runtime."))
    outputs["review_package"] = build_runtime_pr_creator_plugin(goal, outputs["repository_package"], requested_by=requested_by)
    timeline.append(_timeline_event(11, "review_package", outputs["review_package"].get("status", "review_package_ready"), "BR-EXEC-03 review package is attached to Mission Runtime."))
    outputs["release_package"] = build_runtime_release_plugin(goal, outputs["review_package"], requested_by=requested_by)
    timeline.append(_timeline_event(12, "release_package", outputs["release_package"].get("status", "release_package_ready"), "BR-EXEC-04 release package is attached to Mission Runtime."))
    timeline.append(_timeline_event(13, "pause", "waiting_for_founder", "Mission Runtime paused for founder review."))

    return {
        "mode": "mission_runtime_v1",
        "scope": scope,
        "mission": {
            "mission_id": mission_id,
            "goal": goal,
            "requested_by": requested_by,
            "created_at": _now(),
            "status": "waiting_for_founder_review",
            "current_stage": "release_package_review",
        },
        "runtime_outputs": outputs,
        "timeline": timeline,
        "next_action": {
            "owner": "founder",
            "action": "Review the BR-EXEC-04 release package before release operations.",
            "handoff_ready": True,
        },
        "runtime_policy": {
            "auto_merge": False,
            "auto_deploy": False,
            "requires_founder_approval": True,
            "requires_external_review": True,
            "requires_smoke_tests": True,
            "reason": "Mission Runtime includes BR-EXEC-04 release packaging and pauses at founder review.",
        },
    }


def format_mission_runtime_markdown(runtime: Dict[str, Any]) -> str:
    mission = runtime.get("mission", {})
    lines = [
        "## Mission Runtime v1",
        "",
        f"**Mission:** {mission.get('mission_id', '')}",
        f"**Goal:** {mission.get('goal', '')}",
        f"**Status:** {mission.get('status', '')}",
        f"**Current stage:** {mission.get('current_stage', '')}",
        "",
        "### Timeline",
    ]
    for event in runtime.get("timeline", []):
        lines.append(f"- {event['step']}. {event['stage']} — {event['status']}: {event['summary']}")
    repo_pkg = runtime.get("runtime_outputs", {}).get("repository_package")
    if repo_pkg:
        lines.extend(["", "### BR-EXEC-02 Repository Package"])
        lines.append(f"- Status: {repo_pkg.get('status')}")
        lines.append(f"- Repository: {repo_pkg.get('repository')}")
        lines.append(f"- Branch: {repo_pkg.get('proposed_branch')}")
    review_pkg = runtime.get("runtime_outputs", {}).get("review_package")
    if review_pkg:
        lines.extend(["", "### BR-EXEC-03 Review Package"])
        lines.append(f"- Status: {review_pkg.get('status')}")
        lines.append(f"- Title: {review_pkg.get('pr_title')}")
        lines.append(f"- Head: {review_pkg.get('head_branch')}")
    release_pkg = runtime.get("runtime_outputs", {}).get("release_package")
    if release_pkg:
        lines.extend(["", "### BR-EXEC-04 Release Package"])
        lines.append(f"- Status: {release_pkg.get('status')}")
        lines.append(f"- Service: {release_pkg.get('service')}")
        lines.append(f"- Region: {release_pkg.get('region')}")
    lines.extend(["", "### Next Action"])
    next_action = runtime.get("next_action", {})
    lines.append(f"- {next_action.get('owner')}: {next_action.get('action')}")
    lines.extend(["", "### Runtime Policy"])
    for key, value in runtime.get("runtime_policy", {}).items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)
