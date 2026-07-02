from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.platform.code_planner.service import DEFAULT_VALIDATION_GATES, package_code_proposal
from app.platform.executive_intelligence.service import build_executive_intelligence_summary
from app.platform.github_execution.service import execute_github_execution, get_github_execution_status, plan_github_execution
from app.platform.repository_intelligence.service import build_file_plan

PRIMARY_REPOSITORY = "tehkst/ai-app-builder-dev"


def build_engineering_execution_summary() -> dict[str, Any]:
    intelligence = _safe(build_executive_intelligence_summary())
    readiness = intelligence.get("readiness") if isinstance(intelligence.get("readiness"), dict) else {}
    return {
        "company": "AI Software Factory",
        "product": "Engineering Execution Engine",
        "milestone": "AEL-05",
        "status": "engineering-execution-ready",
        "purpose": "Execute approved engineering missions through Mission Control using the same governed GitHub capabilities available to this ChatGPT session.",
        "primary_repository": PRIMARY_REPOSITORY,
        "capability_model": _capability_model(readiness),
        "governance": _governance(),
        "endpoints": {
            "summary": "GET /mission-control/engineering-execution",
            "plan": "POST /mission-control/engineering-execution/plan",
            "execute": "POST /mission-control/engineering-execution/execute",
            "status": "POST /mission-control/engineering-execution/status",
        },
        "next_step": "Board Room should create an execution plan after Founder approval, then call the execute endpoint in dry-run or live mode.",
    }


def plan_engineering_execution(payload: dict[str, Any]) -> dict[str, Any]:
    mission = _normalize_mission(payload)
    approval = _normalize_approval(payload)
    planned_at = _now()
    execution_id = _id("ENGEXEC", planned_at, {"mission": mission, "approval": approval})
    file_plan = _safe(build_file_plan({"mission": mission}))
    code_package = _safe(package_code_proposal(_package_payload(payload, mission)))
    github_payload = _github_payload(payload, mission, approval, code_package)
    github_plan = _safe(plan_github_execution(github_payload))
    return {
        "company": "AI Software Factory",
        "product": "Engineering Execution Engine",
        "milestone": "AEL-05",
        "status": "engineering-execution-plan-created",
        "execution_id": execution_id,
        "mission": mission,
        "approval": approval,
        "executive_intelligence": _safe(build_executive_intelligence_summary()),
        "file_plan": file_plan,
        "code_package": _redact_code_package(code_package),
        "github_execution_plan": github_plan,
        "execution_mode": _execution_mode(payload),
        "governance": _governance(),
        "next_step": "Founder approval is required before calling /mission-control/engineering-execution/execute.",
    }


def execute_engineering_execution(payload: dict[str, Any]) -> dict[str, Any]:
    mission = _normalize_mission(payload)
    approval = _normalize_approval(payload)
    executed_at = _now()
    execution_id = str(payload.get("execution_id") or _id("ENGEXEC", executed_at, {"mission": mission, "approval": approval}))
    if approval["status"] != "approved":
        return {
            "company": "AI Software Factory",
            "product": "Engineering Execution Engine",
            "milestone": "AEL-05",
            "status": "blocked-awaiting-founder-approval",
            "execution_id": execution_id,
            "mission": mission,
            "reason": "Founder approval is required before Mission Control can execute engineering work.",
            "github_mutation_attempted": False,
            "next_step": "Approve the mission in Mission Control, then retry execution.",
        }
    code_package = _safe(package_code_proposal(_package_payload(payload, mission)))
    github_payload = _github_payload(payload, mission, approval, code_package)
    github_result = _safe(execute_github_execution(github_payload))
    return {
        "company": "AI Software Factory",
        "product": "Engineering Execution Engine",
        "milestone": "AEL-05",
        "status": _execution_status(github_result),
        "execution_id": execution_id,
        "mission": mission,
        "approval": approval,
        "execution_mode": _execution_mode(payload),
        "github_result": github_result,
        "mission_control_review": _mission_control_review(github_result),
        "merge_allowed": False,
        "next_step": _next_step(github_result),
    }


def get_engineering_execution_status(payload: dict[str, Any]) -> dict[str, Any]:
    github_status = _safe(get_github_execution_status(payload))
    return {
        "company": "AI Software Factory",
        "product": "Engineering Execution Engine",
        "milestone": "AEL-05",
        "status": "tracked",
        "execution_id": str(payload.get("execution_id") or "ENGEXEC-UNSPECIFIED"),
        "github_status": github_status,
        "founder_review_status": str(payload.get("founder_review_status") or "pending"),
        "merge_allowed": False,
        "next_step": "Review the draft PR in Mission Control after CI passes.",
    }


def _github_payload(payload: dict[str, Any], mission: dict[str, str], approval: dict[str, str], code_package: dict[str, Any]) -> dict[str, Any]:
    package = code_package.get("package") if isinstance(code_package.get("package"), dict) else code_package
    proposed_changes = payload.get("write_batch") or payload.get("changes") or package.get("proposed_changes") or []
    return {
        "mission_id": mission["mission_id"],
        "title": mission["title"],
        "repository": str(payload.get("repository") or PRIMARY_REPOSITORY),
        "feature_branch": str(payload.get("feature_branch") or payload.get("branch_name") or _branch_name(mission)),
        "base_branch": str(payload.get("base_branch") or "main"),
        "write_batch": proposed_changes,
        "commit_message": str(payload.get("commit_message") or f"Execute approved mission {mission['mission_id']}"),
        "pr_title": str(payload.get("pr_title") or mission["title"]),
        "pr_body": str(payload.get("pr_body") or _default_pr_body(mission)),
        "validation_gates": payload.get("validation_gates") or DEFAULT_VALIDATION_GATES,
        "approval": approval,
        "approval_status": approval["status"],
        "approved_by": approval["approved_by"],
        "approval_id": approval["approval_id"],
        "live_execution": _bool(payload.get("live_execution"), default=False),
    }


def _package_payload(payload: dict[str, Any], mission: dict[str, str]) -> dict[str, Any]:
    return {
        "mission_id": mission["mission_id"],
        "title": mission["title"],
        "goal": mission["goal"],
        "proposed_changes": payload.get("write_batch") or payload.get("changes") or [],
        "validation_gates": payload.get("validation_gates") or DEFAULT_VALIDATION_GATES,
    }


def _capability_model(readiness: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"capability": "Read Executive Intelligence", "mission_control": True, "guardrail": "generated on request"},
        {"capability": "Read repository context", "mission_control": True, "guardrail": "Repository Intelligence first"},
        {"capability": "Generate implementation plan", "mission_control": True, "guardrail": "plan before mutation"},
        {"capability": "Create feature branch", "mission_control": readiness.get("live_github_write_ready", False), "guardrail": "GitHub token plus Founder approval"},
        {"capability": "Commit code", "mission_control": readiness.get("live_github_write_ready", False), "guardrail": "feature branch only"},
        {"capability": "Open draft PR", "mission_control": readiness.get("live_github_write_ready", False), "guardrail": "no auto-merge"},
        {"capability": "Merge PR", "mission_control": False, "guardrail": "Founder-controlled"},
    ]


def _governance() -> dict[str, Any]:
    return {
        "founder_approval_required": True,
        "main_branch_write_allowed": False,
        "feature_branch_only": True,
        "live_execution_requires_explicit_flag": True,
        "auto_merge_allowed": False,
        "secrets_visible": False,
    }


def _mission_control_review(github_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "pull_request_url": github_result.get("pull_request_url"),
        "pull_request_number": github_result.get("pull_request_number"),
        "summary": "Mission Control should show the PR, files changed, CI status, and Founder review actions.",
        "review_actions": ["approve_merge", "request_changes", "close_pr"],
        "merge_allowed_by_engine": False,
    }


def _execution_status(github_result: dict[str, Any]) -> str:
    status = str(github_result.get("status") or "unknown")
    if status == "github-execution-completed":
        return "engineering-execution-pr-created"
    if status.startswith("blocked"):
        return status
    if status == "dry-run-ready-for-live-github-execution":
        return "engineering-execution-dry-run-ready"
    return f"engineering-execution-{status}"


def _next_step(github_result: dict[str, Any]) -> str:
    status = str(github_result.get("status") or "unknown")
    if status == "dry-run-ready-for-live-github-execution":
        return "Review the dry-run contract, then retry with live_execution=true after Founder approval."
    if status == "github-execution-completed":
        return "Review the draft PR in Mission Control and wait for CI before merge."
    return str(github_result.get("next_step") or "Review execution status in Mission Control.")


def _normalize_mission(payload: dict[str, Any]) -> dict[str, str]:
    source = payload.get("mission") if isinstance(payload.get("mission"), dict) else payload
    return {
        "mission_id": str(source.get("mission_id") or source.get("id") or "MISSION-UNSPECIFIED").strip(),
        "title": str(source.get("title") or source.get("mission_title") or "Approved engineering mission").strip(),
        "goal": str(source.get("goal") or source.get("description") or "Execute approved engineering work.").strip(),
    }


def _normalize_approval(payload: dict[str, Any]) -> dict[str, str]:
    approval = payload.get("approval") if isinstance(payload.get("approval"), dict) else {}
    return {
        "status": str(approval.get("status") or payload.get("approval_status") or "pending").lower().strip(),
        "approved_by": str(approval.get("approved_by") or payload.get("approved_by") or "").strip(),
        "approval_id": str(approval.get("approval_id") or payload.get("approval_id") or "APPROVAL-UNSPECIFIED").strip(),
    }


def _redact_code_package(code_package: dict[str, Any]) -> dict[str, Any]:
    copy = dict(code_package)
    package = copy.get("package") if isinstance(copy.get("package"), dict) else None
    if package and isinstance(package.get("proposed_changes"), list):
        redacted = []
        for item in package["proposed_changes"]:
            if isinstance(item, dict):
                visible = {key: value for key, value in item.items() if key not in {"content", "new_content", "replacement_content"}}
                visible["content_present"] = bool(item.get("content") or item.get("new_content") or item.get("replacement_content"))
                redacted.append(visible)
            else:
                redacted.append(item)
        package["proposed_changes"] = redacted
    return copy


def _execution_mode(payload: dict[str, Any]) -> dict[str, Any]:
    return {"live_execution": _bool(payload.get("live_execution"), default=False), "dry_run_default": True}


def _branch_name(mission: dict[str, str]) -> str:
    raw = f"mission/{mission['mission_id']}-{mission['title']}".lower()
    cleaned = "".join(char if char.isalnum() else "-" for char in raw)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-")[:80]


def _default_pr_body(mission: dict[str, str]) -> str:
    return f"## Summary\nMission {mission['mission_id']}: {mission['title']}\n\n## Governance\nGenerated by Mission Control Engineering Execution Engine. Founder approval and CI pass are required before merge."


def _safe(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "__dict__"):
        return dict(value.__dict__)
    return {"value": value}


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
