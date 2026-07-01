from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.platform.code_planner.service import DEFAULT_VALIDATION_GATES
from app.platform.patch_application.service import REPOSITORY_FULL_NAME


def build_pr_orchestration_summary() -> dict[str, Any]:
    return {
        "company": "AI Software Factory",
        "product": "Autonomous Pull Request Creation",
        "milestone": "GCP-12",
        "status": "pull-request-orchestration-ready",
        "mode": "founder-governed-pr-workflow",
        "purpose": "Turn approved patch applications into GitHub pull request creation plans and execution records.",
        "governance_rule": "Pull requests target main only through feature branches, CI validation, and founder review. Direct main writes are blocked.",
        "endpoints": {
            "summary": "GET /mission-control/pull-requests",
            "prepare": "POST /mission-control/pull-requests/prepare",
            "create": "POST /mission-control/pull-requests/create",
            "status": "POST /mission-control/pull-requests/status",
            "handover": "GET /mission-control/handover",
        },
        "repository": REPOSITORY_FULL_NAME,
        "handover_readiness": {
            "mission_control_primary_workflow": True,
            "requires_github_write_executor": True,
            "requires_ui_login": True,
            "recommended_next": "GCP-13 Founder Mission Control UI with login and PR review queue",
        },
    }


def prepare_pull_request(payload: dict[str, Any]) -> dict[str, Any]:
    prepared_at = _now()
    request = _normalize_pr_request(payload)
    pr_plan_id = _id("PRPLAN", prepared_at, request)
    return {
        "company": "AI Software Factory",
        "product": "Autonomous Pull Request Creation",
        "milestone": "GCP-12",
        "status": "pull-request-plan-prepared",
        "pr_plan_id": pr_plan_id,
        "mission_id": request["mission_id"],
        "repository": REPOSITORY_FULL_NAME,
        "pull_request_plan": {
            "base_branch": "main",
            "head_branch": request["branch_name"],
            "title": request["title"],
            "body": _build_pr_body(request),
            "draft": True,
            "maintainer_can_modify": True,
        },
        "required_before_create": [
            "Feature branch exists",
            "Approved patch application has been applied to the feature branch",
            "Founder approval is recorded",
        ],
        "validation_gates": request["validation_gates"],
        "next_step": "POST /mission-control/pull-requests/create after branch writes exist.",
    }


def create_pull_request_record(payload: dict[str, Any]) -> dict[str, Any]:
    created_at = _now()
    request = _normalize_pr_request(payload)
    approval = _normalize_approval(payload)
    pr_record_id = _id("PRREC", created_at, {"request": request, "approval": approval})

    if approval["status"] != "approved":
        return {
            "company": "AI Software Factory",
            "product": "Autonomous Pull Request Creation",
            "milestone": "GCP-12",
            "status": "blocked-awaiting-founder-approval",
            "pr_record_id": pr_record_id,
            "mission_id": request["mission_id"],
            "approval": approval,
            "pull_request_created": False,
            "next_step": "Record founder approval before PR creation.",
        }

    branch_ready = _bool(payload.get("branch_ready"), default=False)
    if not branch_ready:
        return {
            "company": "AI Software Factory",
            "product": "Autonomous Pull Request Creation",
            "milestone": "GCP-12",
            "status": "blocked-awaiting-feature-branch-writes",
            "pr_record_id": pr_record_id,
            "mission_id": request["mission_id"],
            "feature_branch": request["branch_name"],
            "pull_request_created": False,
            "reason": "GCP-12 defines the PR creation contract. Branch write execution must mark branch_ready=true after applying approved files.",
            "next_step": "Use the GitHub write executor to apply files, then retry PR creation.",
        }

    return {
        "company": "AI Software Factory",
        "product": "Autonomous Pull Request Creation",
        "milestone": "GCP-12",
        "status": "ready-for-github-pr-create",
        "pr_record_id": pr_record_id,
        "mission_id": request["mission_id"],
        "repository": REPOSITORY_FULL_NAME,
        "github_pr_request": {
            "repository_full_name": REPOSITORY_FULL_NAME,
            "head_branch": request["branch_name"],
            "base_branch": "main",
            "title": request["title"],
            "body": _build_pr_body(request),
            "draft": True,
            "maintainer_can_modify": True,
        },
        "pull_request_created": False,
        "execution_note": "Runtime GitHub PR creation is intentionally exposed as a governed contract. The external executor can use this payload to create the PR.",
        "validation_gates": request["validation_gates"],
        "next_step": "GCP-13 Founder Mission Control UI should display this PR request and creation result.",
    }


def get_pull_request_status(payload: dict[str, Any]) -> dict[str, Any]:
    pr_record_id = str(payload.get("pr_record_id") or payload.get("pr_plan_id") or "PRREC-UNSPECIFIED")
    mission_id = str(payload.get("mission_id") or "MISSION-UNSPECIFIED")
    pr_url = str(payload.get("pr_url") or "").strip()
    return {
        "company": "AI Software Factory",
        "product": "Autonomous Pull Request Creation",
        "milestone": "GCP-12",
        "status": "tracked",
        "pr_record_id": pr_record_id,
        "mission_id": mission_id,
        "pull_request": {
            "url": pr_url or None,
            "created": bool(pr_url),
            "ci_status": str(payload.get("ci_status") or "pending"),
            "founder_review_status": str(payload.get("founder_review_status") or "pending"),
            "merge_allowed": False,
        },
        "next_step": "Founder reviews the PR after CI passes.",
    }


def build_gcp_handover_status() -> dict[str, Any]:
    return {
        "company": "AI Software Factory",
        "product": "Mission Control Handover",
        "milestone": "GCP-12",
        "status": "handover-foundation-ready",
        "message": "Mission Control now has planning, repository intelligence, code proposal, patch application, and PR orchestration APIs.",
        "can_move_primary_workflow_to_gcp": True,
        "handover_scope": [
            "Create founder requests in Mission Control",
            "Generate proposals and approval records",
            "Generate repository context and file plans",
            "Generate code patch proposals",
            "Prepare patch application packages",
            "Prepare PR creation records",
        ],
        "still_requires_this_chat_or_external_executor": [
            "Actual GitHub file writes until runtime GitHub credentials are installed inside GCP",
            "Actual PR creation until the GitHub write executor is wired into Cloud Run",
            "Founder login UI until GCP-13",
        ],
        "recommended_next": "GCP-13 Founder Mission Control UI with login, PR review queue, and GitHub executor connection.",
    }


def _normalize_pr_request(payload: dict[str, Any]) -> dict[str, Any]:
    source = payload.get("pr_plan") if isinstance(payload.get("pr_plan"), dict) else payload
    package = source.get("package") if isinstance(source.get("package"), dict) else {}
    mission = source.get("mission") if isinstance(source.get("mission"), dict) else source
    branch_name = str(source.get("branch_name") or package.get("branch_name") or "").strip()
    mission_id = str(mission.get("mission_id") or source.get("mission_id") or "MISSION-UNSPECIFIED").strip()
    title = str(source.get("title") or package.get("pr_title") or mission.get("title") or f"Implement {mission_id}").strip()
    if not branch_name:
        branch_name = _safe_branch_name(mission_id, title)
    changes = source.get("changes") or source.get("proposed_changes") or package.get("proposed_changes") or []
    if not isinstance(changes, list):
        changes = []
    return {
        "mission_id": mission_id,
        "title": title,
        "goal": str(mission.get("goal") or source.get("goal") or "Apply approved Mission Control changes.").strip(),
        "branch_name": branch_name,
        "changes": _normalize_changes(changes),
        "validation_gates": source.get("validation_gates") or package.get("validation_gates") or DEFAULT_VALIDATION_GATES,
    }


def _normalize_changes(changes: list[Any]) -> list[dict[str, str]]:
    normalized = []
    for change in changes:
        if isinstance(change, str):
            normalized.append({"path": change, "operation": "modify", "intent": "Apply approved change."})
        elif isinstance(change, dict):
            normalized.append(
                {
                    "path": str(change.get("path") or "unknown"),
                    "operation": str(change.get("operation") or "modify"),
                    "intent": str(change.get("intent") or change.get("reason") or "Apply approved change."),
                }
            )
    return normalized


def _normalize_approval(payload: dict[str, Any]) -> dict[str, str]:
    approval = payload.get("approval") if isinstance(payload.get("approval"), dict) else {}
    return {
        "status": str(approval.get("status") or payload.get("approval_status") or "pending").lower().strip(),
        "approved_by": str(approval.get("approved_by") or payload.get("approved_by") or "").strip(),
        "approval_id": str(approval.get("approval_id") or payload.get("approval_id") or "APPROVAL-UNSPECIFIED"),
    }


def _build_pr_body(request: dict[str, Any]) -> str:
    changes = request["changes"] or []
    change_lines = "\n".join(f"- `{item['path']}` — {item['intent']}" for item in changes) or "- No file changes listed."
    gates = "\n".join(f"- `{gate}`" for gate in request["validation_gates"])
    return (
        f"## Summary\n{request['goal']}\n\n"
        f"## Proposed changes\n{change_lines}\n\n"
        f"## Validation gates\n{gates}\n\n"
        "## Governance\nGenerated by AI Software Factory Mission Control. Founder review and CI pass are required before merge."
    )


def _safe_branch_name(mission_id: str, title: str) -> str:
    raw = f"mission/{mission_id}-{title}".lower()
    cleaned = "".join(char if char.isalnum() else "-" for char in raw)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-")[:80]


def _bool(value: Any, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower().strip() in {"1", "true", "yes", "y"}
    return default


def _id(prefix: str, timestamp: str, data: Any) -> str:
    digest = hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:12].upper()
    return f"{prefix}-{timestamp[:10].replace('-', '')}-{digest}"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
