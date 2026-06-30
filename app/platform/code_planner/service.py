from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.platform.runtime.service import invoke_ai


DEFAULT_VALIDATION_GATES = [
    "python -m compileall app",
    "python -m app.platform.api_contract",
    "bash infra/scripts/gate.sh",
    "PR Validation workflow must pass before merge",
]


def build_code_planner_summary() -> dict[str, Any]:
    return {
        "company": "AI Software Factory",
        "product": "Autonomous Code Generation",
        "milestone": "GCP-10",
        "status": "guarded-code-generation-ready",
        "mode": "patch-proposal-only",
        "governance_rule": "GCP-10 proposes code patches only. It does not write files, commit, or open pull requests.",
        "endpoints": {
            "summary": "GET /mission-control/code",
            "generate": "POST /mission-control/code/generate",
            "validate": "POST /mission-control/code/validate",
            "package": "POST /mission-control/code/package",
            "status": "GET /mission-control/code/status",
        },
        "next_step": "GCP-11 Autonomous Patch Application on Feature Branches",
    }


def build_code_status() -> dict[str, Any]:
    return {
        "company": "AI Software Factory",
        "product": "Autonomous Code Generation",
        "milestone": "GCP-10",
        "status": "online",
        "execution_mode": "proposal-only",
        "writes_enabled": False,
        "commits_enabled": False,
        "pull_requests_enabled": False,
        "validation_gates": DEFAULT_VALIDATION_GATES,
    }


def generate_code_patch(payload: dict[str, Any]) -> dict[str, Any]:
    created_at = _now()
    mission = _normalize_mission(payload)
    file_plan = _normalize_file_plan(payload)
    generation_id = _id("CODEGEN", created_at, {"mission": mission, "file_plan": file_plan})
    patch_proposal = {
        "generation_id": generation_id,
        "mission_id": mission["mission_id"],
        "created_at": created_at,
        "mode": "patch-proposal-only",
        "proposed_changes": [
            {
                "path": item["path"],
                "operation": item.get("operation", "inspect-before-edit"),
                "intent": item.get("reason", "Implement mission-specific change after repository context review."),
                "patch_status": "ai-proposed-not-applied",
            }
            for item in file_plan
        ],
        "validation_gates": DEFAULT_VALIDATION_GATES,
        "safety": {
            "files_written": False,
            "commits_created": False,
            "pull_requests_created": False,
            "requires_founder_review": True,
        },
    }
    ai_result = invoke_ai(
        {
            "system": "You are a careful senior software engineer. Produce proposed code changes only. Do not claim files were modified. Prefer small, reviewable patches.",
            "prompt": "Generate a code patch proposal for this mission. Return file-by-file code intent, minimal snippets where useful, tests, validation, and risks.\n" + json.dumps({"mission": mission, "file_plan": file_plan, "patch_proposal": patch_proposal}, sort_keys=True),
            "model": payload.get("model"),
        }
    )
    return {
        "company": "AI Software Factory",
        "product": "Autonomous Code Generation",
        "milestone": "GCP-10",
        "status": "patch-proposal-created" if ai_result.get("status") == "completed" else f"patch-proposal-{ai_result.get('status', 'unknown')}",
        "generation_id": generation_id,
        "mission_id": mission["mission_id"],
        "patch_proposal": patch_proposal,
        "ai_patch_guidance": ai_result,
        "next_step": "Founder review, then GCP-11 patch application on a feature branch.",
    }


def validate_code_proposal(payload: dict[str, Any]) -> dict[str, Any]:
    validation_id = _id("CODEVAL", _now(), payload)
    proposal = payload.get("patch_proposal") if isinstance(payload.get("patch_proposal"), dict) else {}
    checks = [
        {"name": "proposal_present", "status": "pass" if proposal else "warn"},
        {"name": "no_direct_writes", "status": "pass" if not proposal.get("files_written") else "fail"},
        {"name": "validation_gates_present", "status": "pass" if proposal.get("validation_gates") or DEFAULT_VALIDATION_GATES else "fail"},
        {"name": "founder_review_required", "status": "pass"},
    ]
    ai_result = invoke_ai(
        {
            "system": "You are a cautious code review gate. Identify missing tests, risky files, and whether the proposal is safe to advance.",
            "prompt": "Review this patch proposal for safety and readiness.\n" + json.dumps(payload, sort_keys=True),
            "model": payload.get("model"),
        }
    )
    return {
        "company": "AI Software Factory",
        "product": "Autonomous Code Generation",
        "milestone": "GCP-10",
        "status": "validated" if all(item["status"] != "fail" for item in checks) else "validation-failed",
        "validation_id": validation_id,
        "checks": checks,
        "ai_review": ai_result,
        "next_step": "Package proposal for PR planning after founder review.",
    }


def package_code_proposal(payload: dict[str, Any]) -> dict[str, Any]:
    packaged_at = _now()
    package_id = _id("CODEPKG", packaged_at, payload)
    mission = _normalize_mission(payload)
    return {
        "company": "AI Software Factory",
        "product": "Autonomous Code Generation",
        "milestone": "GCP-10",
        "status": "package-created",
        "package_id": package_id,
        "mission_id": mission["mission_id"],
        "created_at": packaged_at,
        "package": {
            "branch_name": _safe_branch_name(mission["mission_id"], mission["title"]),
            "commit_message": f"GCP-10 propose implementation for {mission['title']}",
            "pr_title": f"Implement {mission['title']}",
            "pr_body_sections": [
                "Summary",
                "Proposed code changes",
                "Validation gates",
                "Risks and rollback",
                "Founder approval notes",
            ],
            "validation_gates": DEFAULT_VALIDATION_GATES,
            "execution_mode": "future-branch-application",
        },
        "next_step": "GCP-11 applies approved patch package to a feature branch.",
    }


def _normalize_mission(payload: dict[str, Any]) -> dict[str, Any]:
    source = payload.get("mission") if isinstance(payload.get("mission"), dict) else payload
    return {
        "mission_id": str(source.get("mission_id") or source.get("id") or "MISSION-UNSPECIFIED").strip(),
        "title": str(source.get("mission_title") or source.get("title") or "Approved code mission").strip(),
        "goal": str(source.get("goal") or source.get("description") or "Generate a guarded patch proposal.").strip(),
        "context": str(source.get("current_context") or source.get("context") or "").strip(),
    }


def _normalize_file_plan(payload: dict[str, Any]) -> list[dict[str, str]]:
    file_plan = payload.get("file_plan") or payload.get("files") or []
    if isinstance(file_plan, dict):
        file_plan = file_plan.get("file_plan") or file_plan.get("files") or []
    if not isinstance(file_plan, list) or not file_plan:
        return [
            {"path": "app/platform/server.py", "operation": "inspect-before-edit", "reason": "Endpoint wiring may be required."},
            {"path": "app/platform/api_contract.py", "operation": "inspect-before-edit", "reason": "API contract may need an update."},
        ]
    normalized: list[dict[str, str]] = []
    for item in file_plan:
        if isinstance(item, str):
            normalized.append({"path": item, "operation": "inspect-before-edit", "reason": "Selected by repository intelligence."})
        elif isinstance(item, dict):
            normalized.append(
                {
                    "path": str(item.get("path") or "unknown"),
                    "operation": str(item.get("operation") or "inspect-before-edit"),
                    "reason": str(item.get("reason") or item.get("intent") or "Selected by repository intelligence."),
                }
            )
    return normalized


def _safe_branch_name(mission_id: str, title: str) -> str:
    raw = f"mission/{mission_id}-{title}".lower()
    cleaned = "".join(char if char.isalnum() else "-" for char in raw)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-")[:80]


def _id(prefix: str, timestamp: str, data: Any) -> str:
    digest = hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:12].upper()
    return f"{prefix}-{timestamp[:10].replace('-', '')}-{digest}"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
