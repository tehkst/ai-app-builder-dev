from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.platform.services.code_executor import create_code_execution_plan


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(text: str) -> str:
    value = "".join(ch.lower() if ch.isalnum() else "-" for ch in text).strip("-")
    while "--" in value:
        value = value.replace("--", "-")
    return value[:56] or "mission"


def _approval_id(goal: str) -> str:
    return f"repo-exec-{_slug(goal)}"


def _readiness_checks(execution_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    policy = execution_plan.get("executor_policy", {})
    checks = [
        {
            "key": "dry_run_only",
            "status": "pass" if policy.get("safe_to_execute") is False else "fail",
            "description": "Gateway must remain dry-run only in BR-AI-09A.",
        },
        {
            "key": "no_commit_enabled",
            "status": "pass" if policy.get("safe_to_commit") is False else "fail",
            "description": "Commit execution must remain disabled.",
        },
        {
            "key": "no_pr_enabled",
            "status": "pass" if policy.get("safe_to_open_pr") is False else "fail",
            "description": "PR creation must remain disabled.",
        },
        {
            "key": "human_review_required",
            "status": "pass" if policy.get("requires_human_review") is True else "fail",
            "description": "Human review is required before repository execution.",
        },
    ]
    return checks


def _audit_events(goal: str, execution_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {
            "event": "approval_gateway_created",
            "timestamp": _now(),
            "actor": "mission_control",
            "goal": goal,
            "mode": "dry_run",
        },
        {
            "event": "execution_plan_attached",
            "timestamp": _now(),
            "actor": "code_executor_v1",
            "branch_intent": execution_plan.get("repository_intent", {}).get("proposed_branch"),
        },
        {
            "event": "write_actions_blocked",
            "timestamp": _now(),
            "actor": "repository_executor_gateway",
            "reason": "BR-AI-09A allows approval preparation only; repository writes are disabled.",
        },
    ]


def create_repository_executor_approval_gateway(
    *,
    goal: str,
    requested_by: str = "founder",
    db: Optional[Session] = None,
    scope: str = "mission_control",
) -> Dict[str, Any]:
    execution_plan = create_code_execution_plan(goal=goal, db=db, scope=scope)
    readiness_checks = _readiness_checks(execution_plan)
    ready_for_human_review = all(check["status"] == "pass" for check in readiness_checks)
    return {
        "mode": "repository_executor_approval_gateway_v1",
        "scope": scope,
        "goal": goal,
        "approval_request": {
            "approval_id": _approval_id(goal),
            "requested_by": requested_by,
            "requested_at": _now(),
            "status": "pending_founder_review",
            "approval_required_for": [
                "create_branch",
                "write_files",
                "commit_changes",
                "open_pull_request",
            ],
        },
        "execution_plan": execution_plan,
        "readiness_checks": readiness_checks,
        "ready_for_human_review": ready_for_human_review,
        "audit_events": _audit_events(goal, execution_plan),
        "gateway_policy": {
            "dry_run_only": True,
            "repository_writes_enabled": False,
            "branch_creation_enabled": False,
            "commit_enabled": False,
            "pull_request_enabled": False,
            "requires_explicit_founder_approval": True,
            "reason": "BR-AI-09A creates the approval gateway and audit contract only. Execution remains disabled until the next governed executor milestone.",
        },
    }


def format_gateway_markdown(gateway: Dict[str, Any]) -> str:
    approval = gateway.get("approval_request", {})
    lines = [
        "## Repository Executor Approval Gateway",
        "",
        f"**Goal:** {gateway.get('goal', '')}",
        f"**Approval ID:** {approval.get('approval_id', '')}",
        f"**Status:** {approval.get('status', '')}",
        f"**Ready for human review:** {gateway.get('ready_for_human_review')}",
        "",
        "### Readiness Checks",
    ]
    for check in gateway.get("readiness_checks", []):
        lines.append(f"- {check['key']}: {check['status']} — {check['description']}")
    lines.extend(["", "### Gateway Policy"])
    for key, value in gateway.get("gateway_policy", {}).items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)
