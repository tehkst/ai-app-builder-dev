from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.platform.services.mission_runtime import run_mission_runtime


def _compact_timeline(runtime: Dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "step": event.get("step"),
            "stage": event.get("stage"),
            "status": event.get("status"),
            "summary": event.get("summary"),
        }
        for event in runtime.get("timeline", [])
    ]


def create_mission_runtime_workbench(
    *,
    goal: str,
    requested_by: str = "founder",
    sprint_days: int = 7,
    capacity_points: int = 20,
    db: Optional[Session] = None,
    scope: str = "mission_control",
) -> Dict[str, Any]:
    runtime = run_mission_runtime(
        goal=goal,
        requested_by=requested_by,
        sprint_days=sprint_days,
        capacity_points=capacity_points,
        db=db,
        scope=scope,
    )
    outputs = runtime.get("runtime_outputs", {})
    pr_handoff = outputs.get("pr_handoff", {})
    approval_gateway = outputs.get("approval_gateway", {})
    sprint = outputs.get("sprint", {})
    return {
        "mode": "mission_runtime_workbench_v1",
        "mission": runtime.get("mission", {}),
        "founder_view": {
            "goal": goal,
            "status": runtime.get("mission", {}).get("status"),
            "current_stage": runtime.get("mission", {}).get("current_stage"),
            "next_action": runtime.get("next_action", {}),
            "timeline": _compact_timeline(runtime),
            "committed_stories": sprint.get("committed_stories", []),
            "approval_request": approval_gateway.get("approval_request", {}),
            "pr_handoff": pr_handoff.get("handoff", {}),
            "handoff_policy": pr_handoff.get("handoff_policy", {}),
            "runtime_policy": runtime.get("runtime_policy", {}),
        },
        "full_runtime": runtime,
    }


def format_workbench_markdown(workbench: Dict[str, Any]) -> str:
    view = workbench.get("founder_view", {})
    lines = [
        "## Mission Runtime Workbench",
        "",
        f"**Goal:** {view.get('goal', '')}",
        f"**Status:** {view.get('status', '')}",
        f"**Current stage:** {view.get('current_stage', '')}",
        "",
        "### Timeline",
    ]
    for event in view.get("timeline", []):
        lines.append(f"- {event.get('step')}. {event.get('stage')} — {event.get('status')}: {event.get('summary')}")
    lines.extend(["", "### Next Action"])
    next_action = view.get("next_action", {})
    lines.append(f"- {next_action.get('owner')}: {next_action.get('action')}")
    lines.extend(["", "### PR Handoff"])
    pr = view.get("pr_handoff", {})
    lines.append(f"- Repository: {pr.get('repository', '')}")
    lines.append(f"- Branch: {pr.get('proposed_branch', '')}")
    lines.append(f"- Status: {pr.get('status', '')}")
    return "\n".join(lines)
