from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.platform.services.repository_executor_gateway import create_repository_executor_approval_gateway


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(text: str) -> str:
    value = "".join(ch.lower() if ch.isalnum() else "-" for ch in text).strip("-")
    while "--" in value:
        value = value.replace("--", "-")
    return value[:56] or "mission"


def _branch(goal: str) -> str:
    return f"mission-control/{_slug(goal)}"


def _pr_title(goal: str) -> str:
    return f"Mission Control: {goal[:90]}"


def _handoff_checklist() -> list[dict[str, str]]:
    return [
        {"item": "Branch prepared", "status": "pending_approval"},
        {"item": "Implementation package reviewed", "status": "pending_approval"},
        {"item": "Protected boundaries confirmed", "status": "required"},
        {"item": "PR opened for external review", "status": "blocked_until_execution_enabled"},
        {"item": "No auto-merge", "status": "enforced"},
        {"item": "No auto-deploy", "status": "enforced"},
    ]


def create_pr_handoff(
    *,
    goal: str,
    requested_by: str = "founder",
    db: Optional[Session] = None,
    scope: str = "mission_control",
) -> Dict[str, Any]:
    gateway = create_repository_executor_approval_gateway(
        goal=goal,
        requested_by=requested_by,
        db=db,
        scope=scope,
    )
    execution_plan = gateway.get("execution_plan", {})
    repo_intent = execution_plan.get("repository_intent", {})
    proposed_branch = repo_intent.get("proposed_branch") or _branch(goal)
    pr_body = repo_intent.get("pr_body") or "Mission Control generated handoff for founder review."
    return {
        "mode": "branch_pr_handoff_executor_v1",
        "scope": scope,
        "goal": goal,
        "handoff": {
            "handoff_id": f"handoff-{_slug(goal)}",
            "created_at": _now(),
            "requested_by": requested_by,
            "status": "ready_for_founder_approval",
            "repository": repo_intent.get("target_repository", "tehkst/ai-app-builder-dev"),
            "base_branch": repo_intent.get("base_branch", "main"),
            "proposed_branch": proposed_branch,
            "pr_title": repo_intent.get("pr_title") or _pr_title(goal),
            "pr_body": pr_body,
        },
        "approval_gateway": gateway,
        "checklist": _handoff_checklist(),
        "external_review": {
            "reviewer": "ChatGPT or human reviewer",
            "review_required_before_merge": True,
            "founder_merge_required": True,
        },
        "handoff_policy": {
            "can_create_branch": False,
            "can_write_files": False,
            "can_open_pr": False,
            "can_auto_merge": False,
            "can_auto_deploy": False,
            "requires_founder_approval": True,
            "reason": "BR-AI-11 creates the supervised branch and PR handoff contract. Actual branch creation and PR writes remain gated until explicit execution approval is enabled.",
        },
        "next_actions": [
            "Founder reviews handoff contract.",
            "External reviewer inspects the proposed scope and protected boundaries.",
            "After approval, a governed executor milestone can enable branch and PR creation.",
        ],
    }


def format_pr_handoff_markdown(handoff: Dict[str, Any]) -> str:
    info = handoff.get("handoff", {})
    lines = [
        "## Branch + PR Handoff Executor",
        "",
        f"**Goal:** {handoff.get('goal', '')}",
        f"**Status:** {info.get('status', '')}",
        f"**Repository:** {info.get('repository', '')}",
        f"**Branch:** {info.get('proposed_branch', '')}",
        f"**PR title:** {info.get('pr_title', '')}",
        "",
        "### Checklist",
    ]
    for item in handoff.get("checklist", []):
        lines.append(f"- {item['item']}: {item['status']}")
    lines.extend(["", "### Handoff Policy"])
    for key, value in handoff.get("handoff_policy", {}).items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)
