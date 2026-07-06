from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.platform.services.mission_runtime_workbench import create_mission_runtime_workbench


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_execution_readiness(
    *,
    goal: str,
    requested_by: str = "founder",
    sprint_days: int = 7,
    capacity_points: int = 20,
    db: Optional[Session] = None,
    scope: str = "mission_control",
) -> Dict[str, Any]:
    workbench = create_mission_runtime_workbench(
        goal=goal,
        requested_by=requested_by,
        sprint_days=sprint_days,
        capacity_points=capacity_points,
        db=db,
        scope=scope,
    )
    mission = workbench.get("mission", {})
    view = workbench.get("founder_view", {})
    return {
        "mode": "mission_runtime_v2_execution_readiness",
        "mission": {
            "mission_id": mission.get("mission_id"),
            "goal": goal,
            "requested_by": requested_by,
            "created_at": _now(),
            "status": "ready_for_supervised_execution_review",
            "current_stage": "approval_review",
        },
        "workbench": workbench,
        "readiness_stages": [
            {"stage": "mission_plan", "status": "complete", "gate": "none"},
            {"stage": "engineering_plan", "status": "complete", "gate": "none"},
            {"stage": "implementation_package", "status": "complete", "gate": "external_review"},
            {"stage": "handoff_contract", "status": "complete", "gate": "founder_review"},
            {"stage": "repository_execution", "status": "not_enabled", "gate": "future_executor_governance"},
            {"stage": "merge", "status": "not_enabled", "gate": "manual_founder_action"},
            {"stage": "production_deploy", "status": "not_enabled", "gate": "future_deploy_runtime"},
            {"stage": "smoke_test", "status": "not_enabled", "gate": "future_qa_runtime"},
        ],
        "approval_state": {
            "approval_required": True,
            "approval_owner": "founder",
            "external_review_required": True,
            "approval_request": view.get("approval_request", {}),
            "pr_handoff": view.get("pr_handoff", {}),
        },
        "audit_trail": [
            {"event": "execution_readiness_created", "timestamp": _now(), "actor": "mission_runtime_v2"},
            {"event": "supervised_mode_enforced", "timestamp": _now(), "actor": "governance"},
            {"event": "repository_write_execution_not_enabled", "timestamp": _now(), "actor": "governance"},
        ],
        "execution_policy": {
            "supervised_mode": True,
            "repository_write_execution_enabled": False,
            "auto_merge_enabled": False,
            "auto_deploy_enabled": False,
            "founder_review_required": True,
            "external_review_required": True,
            "reason": "Mission Runtime v2 creates the execution-readiness gate and lifecycle model. Actual repository writing, merge, deployment, and smoke-test automation remain separate governed milestones.",
        },
        "next_action": {
            "owner": "founder",
            "action": "Review the workbench, approval state, and PR handoff before enabling a future governed executor.",
        },
    }


def format_execution_readiness_markdown(runtime: Dict[str, Any]) -> str:
    mission = runtime.get("mission", {})
    lines = [
        "## Mission Runtime v2 — Execution Readiness",
        "",
        f"**Mission:** {mission.get('mission_id', '')}",
        f"**Goal:** {mission.get('goal', '')}",
        f"**Status:** {mission.get('status', '')}",
        "",
        "### Readiness Stages",
    ]
    for stage in runtime.get("readiness_stages", []):
        lines.append(f"- {stage['stage']} — {stage['status']} ({stage['gate']})")
    lines.extend(["", "### Policy"])
    for key, value in runtime.get("execution_policy", {}).items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)
