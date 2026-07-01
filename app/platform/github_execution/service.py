from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any

from app.platform.code_planner.service import DEFAULT_VALIDATION_GATES
from app.platform.patch_application.service import REPOSITORY_FULL_NAME

GITHUB_TOKEN_SECRET_NAME = "GITHUB_TOKEN"
DEFAULT_BASE_BRANCH = "main"


def build_github_execution_summary() -> dict[str, Any]:
    configured = _github_configured()
    return {
        "company": "AI Software Factory",
        "product": "Autonomous GitHub Execution Engine",
        "milestone": "GCP-14",
        "status": "executor-configured" if configured else "executor-awaiting-github-token",
        "mode": "feature-branch-only",
        "repository": REPOSITORY_FULL_NAME,
        "secret_name": GITHUB_TOKEN_SECRET_NAME,
        "github_token_present": configured,
        "github_token_visible": False,
        "governance_rule": "The executor may prepare feature-branch writes and PR creation only after founder approval. Direct writes to main are blocked.",
        "endpoints": {
            "summary": "GET /mission-control/github-executor",
            "plan": "POST /mission-control/github-executor/plan",
            "execute": "POST /mission-control/github-executor/execute",
            "status": "POST /mission-control/github-executor/status",
        },
        "capabilities": [
            "feature-branch-planning",
            "file-write-batch-contract",
            "commit-contract",
            "pull-request-contract",
            "ci-gate-contract",
        ],
        "safety": {
            "main_branch_write_allowed": False,
            "founder_approval_required": True,
            "ci_required": True,
            "secrets_hidden": True,
        },
        "next_step": "Mount GITHUB_TOKEN in Cloud Run Secret Manager, then execute approved feature-branch write batches.",
    }


def plan_github_execution(payload: dict[str, Any]) -> dict[str, Any]:
    planned_at = _now()
    execution = _normalize_execution(payload)
    execution_id = _id("GHXPLAN", planned_at, execution)
    return {
        "company": "AI Software Factory",
        "product": "Autonomous GitHub Execution Engine",
        "milestone": "GCP-14",
        "status": "github-execution-plan-created",
        "execution_id": execution_id,
        "mission_id": execution["mission_id"],
        "repository": execution["repository"],
        "branch_plan": {
            "base_branch": execution["base_branch"],
            "feature_branch": execution["feature_branch"],
            "main_branch_write_allowed": False,
        },
        "write_batch": execution["write_batch"],
        "commit": {
            "message": execution["commit_message"],
            "author": "AI Software Factory Mission Control",
        },
        "pull_request": {
            "title": execution["pr_title"],
            "body": execution["pr_body"],
            "draft": True,
            "base_branch": execution["base_branch"],
            "head_branch": execution["feature_branch"],
        },
        "validation_gates": execution["validation_gates"],
        "required_secrets": [GITHUB_TOKEN_SECRET_NAME],
        "next_step": "POST /mission-control/github-executor/execute with founder approval after GITHUB_TOKEN is mounted.",
    }


def execute_github_execution(payload: dict[str, Any]) -> dict[str, Any]:
    executed_at = _now()
    execution = _normalize_execution(payload)
    approval = _normalize_approval(payload)
    execution_id = str(payload.get("execution_id") or _id("GHXEXEC", executed_at, {"execution": execution, "approval": approval}))

    if approval["status"] != "approved":
        return _blocked(
            execution_id=execution_id,
            execution=execution,
            status="blocked-awaiting-founder-approval",
            reason="Founder approval is required before GitHub execution.",
        )

    if execution["base_branch"] != DEFAULT_BASE_BRANCH:
        return _blocked(
            execution_id=execution_id,
            execution=execution,
            status="blocked-invalid-base-branch",
            reason="Only main is accepted as the protected PR base branch.",
        )

    if execution["feature_branch"] in {"main", "master", DEFAULT_BASE_BRANCH}:
        return _blocked(
            execution_id=execution_id,
            execution=execution,
            status="blocked-main-branch-write",
            reason="GitHub execution cannot write directly to main.",
        )

    if not _github_configured():
        return {
            "company": "AI Software Factory",
            "product": "Autonomous GitHub Execution Engine",
            "milestone": "GCP-14",
            "status": "blocked-missing-github-token",
            "execution_id": execution_id,
            "mission_id": execution["mission_id"],
            "repository": execution["repository"],
            "secret_name": GITHUB_TOKEN_SECRET_NAME,
            "github_token_present": False,
            "github_token_visible": False,
            "planned_operations": _planned_operations(execution),
            "writes_performed": False,
            "pull_request_created": False,
            "next_step": "Create secret GITHUB_TOKEN in Google Secret Manager and mount it into Cloud Run.",
        }

    return {
        "company": "AI Software Factory",
        "product": "Autonomous GitHub Execution Engine",
        "milestone": "GCP-14",
        "status": "ready-for-live-github-execution",
        "execution_id": execution_id,
        "mission_id": execution["mission_id"],
        "repository": execution["repository"],
        "github_token_present": True,
        "github_token_visible": False,
        "planned_operations": _planned_operations(execution),
        "execution_contract": {
            "create_branch": {
                "repository_full_name": execution["repository"],
                "branch_name": execution["feature_branch"],
                "base_ref": execution["base_branch"],
            },
            "write_files": execution["write_batch"],
            "commit_message": execution["commit_message"],
            "create_pull_request": {
                "repository_full_name": execution["repository"],
                "head_branch": execution["feature_branch"],
                "base_branch": execution["base_branch"],
                "title": execution["pr_title"],
                "body": execution["pr_body"],
                "draft": True,
                "maintainer_can_modify": True,
            },
        },
        "writes_performed": False,
        "pull_request_created": False,
        "note": "GCP-14 installs the governed execution contract inside Cloud Run. The next hotfix connects this contract to live GitHub REST calls using the mounted token.",
        "next_step": "GCP-14A Live GitHub REST Executor: perform branch writes and PR creation from this contract.",
    }


def get_github_execution_status(payload: dict[str, Any]) -> dict[str, Any]:
    execution_id = str(payload.get("execution_id") or "GHXEXEC-UNSPECIFIED")
    pr_url = str(payload.get("pr_url") or "").strip()
    return {
        "company": "AI Software Factory",
        "product": "Autonomous GitHub Execution Engine",
        "milestone": "GCP-14",
        "status": "tracked",
        "execution_id": execution_id,
        "state": {
            "branch_created": _bool(payload.get("branch_created"), default=False),
            "files_written": _bool(payload.get("files_written"), default=False),
            "commit_created": _bool(payload.get("commit_created"), default=False),
            "pull_request_created": bool(pr_url),
            "pull_request_url": pr_url or None,
            "ci_status": str(payload.get("ci_status") or "pending"),
            "founder_review_status": str(payload.get("founder_review_status") or "pending"),
        },
        "merge_allowed": False,
        "next_step": "Wait for CI pass and founder review before merge.",
    }


def _normalize_execution(payload: dict[str, Any]) -> dict[str, Any]:
    source = payload.get("execution") if isinstance(payload.get("execution"), dict) else payload
    mission = source.get("mission") if isinstance(source.get("mission"), dict) else source
    package = source.get("package") if isinstance(source.get("package"), dict) else {}
    pr = source.get("pull_request") if isinstance(source.get("pull_request"), dict) else {}
    mission_id = str(mission.get("mission_id") or source.get("mission_id") or package.get("mission_id") or "MISSION-UNSPECIFIED").strip()
    title = str(source.get("title") or mission.get("title") or pr.get("title") or f"Implement {mission_id}").strip()
    feature_branch = str(source.get("feature_branch") or source.get("branch_name") or package.get("branch_name") or pr.get("head_branch") or _safe_branch_name(mission_id, title)).strip()
    base_branch = str(source.get("base_branch") or pr.get("base_branch") or DEFAULT_BASE_BRANCH).strip()
    changes = source.get("write_batch") or source.get("changes") or source.get("proposed_changes") or package.get("proposed_changes") or []
    return {
        "mission_id": mission_id,
        "title": title,
        "repository": str(source.get("repository") or source.get("repository_full_name") or REPOSITORY_FULL_NAME),
        "base_branch": base_branch,
        "feature_branch": feature_branch,
        "write_batch": _normalize_write_batch(changes),
        "commit_message": str(source.get("commit_message") or package.get("commit_message") or f"Apply approved mission changes for {mission_id}"),
        "pr_title": str(pr.get("title") or source.get("pr_title") or title),
        "pr_body": str(pr.get("body") or source.get("pr_body") or _default_pr_body(mission_id, title, changes)),
        "validation_gates": source.get("validation_gates") or package.get("validation_gates") or DEFAULT_VALIDATION_GATES,
    }


def _normalize_write_batch(changes: Any) -> list[dict[str, str]]:
    if not isinstance(changes, list):
        changes = []
    normalized: list[dict[str, str]] = []
    for change in changes:
        if isinstance(change, str):
            normalized.append({"path": change, "operation": "modify", "content_source": "generated-patch", "intent": "Apply approved change."})
        elif isinstance(change, dict):
            normalized.append(
                {
                    "path": str(change.get("path") or "unknown"),
                    "operation": str(change.get("operation") or "modify"),
                    "content_source": str(change.get("content_source") or change.get("source") or "generated-patch"),
                    "intent": str(change.get("intent") or change.get("reason") or "Apply approved change."),
                }
            )
    if not normalized:
        normalized = [
            {"path": "app/platform/server.py", "operation": "modify", "content_source": "generated-patch", "intent": "Wire approved Mission Control change."},
            {"path": "app/platform/api_contract.py", "operation": "modify", "content_source": "generated-patch", "intent": "Update API contract."},
        ]
    return normalized


def _normalize_approval(payload: dict[str, Any]) -> dict[str, str]:
    approval = payload.get("approval") if isinstance(payload.get("approval"), dict) else {}
    return {
        "status": str(approval.get("status") or payload.get("approval_status") or "pending").lower().strip(),
        "approved_by": str(approval.get("approved_by") or payload.get("approved_by") or "").strip(),
        "approval_id": str(approval.get("approval_id") or payload.get("approval_id") or "APPROVAL-UNSPECIFIED"),
    }


def _blocked(*, execution_id: str, execution: dict[str, Any], status: str, reason: str) -> dict[str, Any]:
    return {
        "company": "AI Software Factory",
        "product": "Autonomous GitHub Execution Engine",
        "milestone": "GCP-14",
        "status": status,
        "execution_id": execution_id,
        "mission_id": execution["mission_id"],
        "repository": execution["repository"],
        "reason": reason,
        "writes_performed": False,
        "pull_request_created": False,
    }


def _planned_operations(execution: dict[str, Any]) -> list[dict[str, str]]:
    operations = [
        {"operation": "create_feature_branch", "target": execution["feature_branch"]},
    ]
    operations.extend({"operation": f"write_{item['operation']}", "target": item["path"]} for item in execution["write_batch"])
    operations.append({"operation": "create_commit", "target": execution["feature_branch"]})
    operations.append({"operation": "open_pull_request", "target": execution["pr_title"]})
    operations.append({"operation": "wait_for_ci", "target": "PR Validation"})
    return operations


def _default_pr_body(mission_id: str, title: str, changes: Any) -> str:
    return (
        f"## Summary\nMission {mission_id}: {title}\n\n"
        "## Governance\nGenerated by AI Software Factory Mission Control. Founder approval and CI pass are required before merge."
    )


def _safe_branch_name(mission_id: str, title: str) -> str:
    raw = f"mission/{mission_id}-{title}".lower()
    cleaned = "".join(char if char.isalnum() else "-" for char in raw)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-")[:80]


def _github_configured() -> bool:
    return bool(os.getenv(GITHUB_TOKEN_SECRET_NAME))


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
