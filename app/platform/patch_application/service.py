from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.platform.code_planner.service import DEFAULT_VALIDATION_GATES


REPOSITORY_FULL_NAME = "tehkst/ai-app-builder-dev"


def build_patch_application_summary() -> dict[str, Any]:
    return {
        "company": "AI Software Factory",
        "product": "Autonomous Patch Application",
        "milestone": "GCP-11",
        "status": "patch-application-ready",
        "mode": "feature-branch-governed",
        "governance_rule": "Approved patches may be prepared for feature branches only. main remains protected by CI and founder merge approval.",
        "endpoints": {
            "summary": "GET /mission-control/patches",
            "prepare": "POST /mission-control/patches/prepare",
            "apply": "POST /mission-control/patches/apply",
            "status": "POST /mission-control/patches/status",
        },
        "repository": REPOSITORY_FULL_NAME,
        "safety": {
            "writes_to_main": False,
            "feature_branch_required": True,
            "founder_approval_required": True,
            "ci_required": True,
        },
        "next_step": "GCP-12 Autonomous Pull Request Creation",
    }


def prepare_patch_application(payload: dict[str, Any]) -> dict[str, Any]:
    prepared_at = _now()
    package = _normalize_package(payload)
    application_id = _id("PATCHAPP", prepared_at, package)
    branch_name = package.get("branch_name") or _safe_branch_name(package["mission_id"], package["title"])
    return {
        "company": "AI Software Factory",
        "product": "Autonomous Patch Application",
        "milestone": "GCP-11",
        "status": "application-prepared",
        "application_id": application_id,
        "mission_id": package["mission_id"],
        "repository": REPOSITORY_FULL_NAME,
        "branch_plan": {
            "base_branch": "main",
            "feature_branch": branch_name,
            "branch_operation": "create-or-reuse-feature-branch",
            "main_branch_write_allowed": False,
        },
        "patch_plan": {
            "source_generation_id": package.get("generation_id"),
            "changes": package["changes"],
            "commit_message": package.get("commit_message") or f"Apply approved patch for {package['title']}",
        },
        "validation_gates": package.get("validation_gates") or DEFAULT_VALIDATION_GATES,
        "approval_gate": {
            "required": True,
            "approval_source": "Founder Approval Workflow",
            "minimum_status": "approved",
        },
        "next_step": "POST /mission-control/patches/apply after founder approval.",
    }


def apply_patch_application(payload: dict[str, Any]) -> dict[str, Any]:
    applied_at = _now()
    package = _normalize_package(payload)
    approval = _normalize_approval(payload)
    application_id = str(payload.get("application_id") or _id("PATCHAPP", applied_at, package))
    branch_name = str(payload.get("branch_name") or package.get("branch_name") or _safe_branch_name(package["mission_id"], package["title"]))

    if approval["status"] != "approved":
        return {
            "company": "AI Software Factory",
            "product": "Autonomous Patch Application",
            "milestone": "GCP-11",
            "status": "blocked-awaiting-founder-approval",
            "application_id": application_id,
            "mission_id": package["mission_id"],
            "approval": approval,
            "writes_performed": False,
            "next_step": "Approve the patch package before applying it to a feature branch.",
        }

    return {
        "company": "AI Software Factory",
        "product": "Autonomous Patch Application",
        "milestone": "GCP-11",
        "status": "ready-for-github-branch-application",
        "application_id": application_id,
        "mission_id": package["mission_id"],
        "repository": REPOSITORY_FULL_NAME,
        "branch": {
            "base_branch": "main",
            "feature_branch": branch_name,
            "write_target": branch_name,
            "main_branch_write_allowed": False,
        },
        "changes_to_apply": [
            {
                "path": change["path"],
                "operation": change.get("operation", "modify"),
                "status": "queued-for-feature-branch-write",
                "intent": change.get("intent", "Apply approved patch."),
            }
            for change in package["changes"]
        ],
        "commit": {
            "message": package.get("commit_message") or f"Apply approved patch for {package['title']}",
            "created": False,
            "reason": "GCP-11 exposes the governed application contract. Connector-level write execution is enabled in GCP-12 PR creation.",
        },
        "validation_gates": package.get("validation_gates") or DEFAULT_VALIDATION_GATES,
        "writes_performed": False,
        "next_step": "GCP-12 will execute branch writes and open the pull request.",
    }


def get_patch_application_status(payload: dict[str, Any]) -> dict[str, Any]:
    application_id = str(payload.get("application_id") or "PATCHAPP-UNSPECIFIED")
    mission_id = str(payload.get("mission_id") or "MISSION-UNSPECIFIED")
    return {
        "company": "AI Software Factory",
        "product": "Autonomous Patch Application",
        "milestone": "GCP-11",
        "status": "tracked",
        "application_id": application_id,
        "mission_id": mission_id,
        "state": {
            "feature_branch_prepared": True,
            "patches_ready": True,
            "writes_performed": False,
            "pr_created": False,
            "founder_approval_required": True,
        },
        "next_step": "Use GCP-12 to create the branch writes and pull request.",
    }


def _normalize_package(payload: dict[str, Any]) -> dict[str, Any]:
    source = payload.get("package") if isinstance(payload.get("package"), dict) else payload
    mission = source.get("mission") if isinstance(source.get("mission"), dict) else source
    patch_proposal = source.get("patch_proposal") if isinstance(source.get("patch_proposal"), dict) else {}
    package_payload = source.get("package") if isinstance(source.get("package"), dict) else {}
    changes = patch_proposal.get("proposed_changes") or source.get("proposed_changes") or source.get("changes") or []
    if not isinstance(changes, list):
        changes = []
    normalized_changes = []
    for change in changes:
        if isinstance(change, str):
            normalized_changes.append({"path": change, "operation": "modify", "intent": "Apply approved patch."})
        elif isinstance(change, dict):
            normalized_changes.append(
                {
                    "path": str(change.get("path") or "unknown"),
                    "operation": str(change.get("operation") or "modify"),
                    "intent": str(change.get("intent") or change.get("reason") or "Apply approved patch."),
                }
            )
    if not normalized_changes:
        normalized_changes = [
            {"path": "app/platform/server.py", "operation": "modify", "intent": "Wire approved API changes."},
            {"path": "app/platform/api_contract.py", "operation": "modify", "intent": "Update API contract."},
        ]
    return {
        "mission_id": str(mission.get("mission_id") or mission.get("id") or patch_proposal.get("mission_id") or "MISSION-UNSPECIFIED"),
        "title": str(mission.get("title") or mission.get("mission_title") or package_payload.get("pr_title") or "Approved patch application"),
        "generation_id": str(patch_proposal.get("generation_id") or source.get("generation_id") or "CODEGEN-UNSPECIFIED"),
        "branch_name": str(package_payload.get("branch_name") or source.get("branch_name") or ""),
        "commit_message": str(package_payload.get("commit_message") or source.get("commit_message") or ""),
        "validation_gates": package_payload.get("validation_gates") or source.get("validation_gates") or DEFAULT_VALIDATION_GATES,
        "changes": normalized_changes,
    }


def _normalize_approval(payload: dict[str, Any]) -> dict[str, str]:
    approval = payload.get("approval") if isinstance(payload.get("approval"), dict) else {}
    status = str(approval.get("status") or payload.get("approval_status") or "pending").lower().strip()
    approved_by = str(approval.get("approved_by") or payload.get("approved_by") or "").strip()
    return {
        "status": status,
        "approved_by": approved_by,
        "approval_id": str(approval.get("approval_id") or payload.get("approval_id") or "APPROVAL-UNSPECIFIED"),
    }


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
