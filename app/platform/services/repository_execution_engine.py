from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.platform.services.github_credential_manager import (
    DEFAULT_REPOSITORY,
    validate_repository_access_request,
    github_credential_status,
)
from app.platform.services.mission_runtime_workbench import create_mission_runtime_workbench


PROTECTED_PATH_PREFIXES = (
    "app/api/routes/auth",
    "app/platform/api/platform_auth",
    "app/platform/security/",
    ".github/workflows/",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(text: str) -> str:
    value = "".join(ch.lower() if ch.isalnum() else "-" for ch in text).strip("-")
    while "--" in value:
        value = value.replace("--", "-")
    return value[:56] or "mission"


def _branch_name(goal: str) -> str:
    return f"mission-control/{_slug(goal)}"


def _is_protected_path(path: str) -> bool:
    normalized = path.strip().lstrip("/")
    return any(normalized.startswith(prefix) for prefix in PROTECTED_PATH_PREFIXES)


def _extract_patches(workbench: Dict[str, Any]) -> List[Dict[str, Any]]:
    runtime = workbench.get("full_runtime", {})
    outputs = runtime.get("runtime_outputs", {})
    package = outputs.get("implementation_package", {})
    patches = package.get("proposed_patches", [])
    normalized: List[Dict[str, Any]] = []
    for index, patch in enumerate(patches, start=1):
        path = patch.get("path") or patch.get("file") or f"unknown-{index}"
        instructions = patch.get("instructions", [])
        if isinstance(instructions, str):
            instructions = [instructions]
        normalized.append(
            {
                "id": f"edit-{index}",
                "path": path,
                "operation": patch.get("patch_type") or patch.get("operation") or "modify",
                "instructions": instructions,
                "protected": _is_protected_path(path),
                "status": "blocked_protected_path" if _is_protected_path(path) else "ready_for_review",
            }
        )
    return normalized


def _diff_preview(edit: Dict[str, Any]) -> str:
    path = edit.get("path", "unknown")
    instructions = edit.get("instructions", [])
    body = "\n".join(f"# {item}" for item in instructions) or "# Apply implementation package instructions."
    return f"--- a/{path}\n+++ b/{path}\n@@ proposed change @@\n{body}\n"


def _risk_level(edits: List[Dict[str, Any]]) -> str:
    if any(edit.get("protected") for edit in edits):
        return "high"
    if len(edits) >= 5:
        return "medium"
    return "low"


def create_repository_execution_package(
    *,
    goal: str,
    repository: str = DEFAULT_REPOSITORY,
    requested_by: str = "founder",
    founder_approved: bool = False,
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
    credential_status = github_credential_status()
    access_checks = [
        validate_repository_access_request(repository, "create_feature_branch", founder_approved),
        validate_repository_access_request(repository, "write_feature_branch_files", founder_approved),
        validate_repository_access_request(repository, "commit_feature_branch_changes", founder_approved),
        validate_repository_access_request(repository, "open_pull_request", founder_approved),
    ]
    edits = _extract_patches(workbench)
    protected_edits = [edit for edit in edits if edit.get("protected")]
    branch = _branch_name(goal)
    can_proceed = bool(edits) and not protected_edits and all(check.get("allowed") for check in access_checks)
    execution_status = "ready_to_execute" if can_proceed else "blocked_pending_requirements"
    blocking_reasons: List[str] = []
    if not edits:
        blocking_reasons.append("No implementation edit operations were generated.")
    if protected_edits:
        blocking_reasons.append("One or more proposed edits target protected paths and require a protected security mission.")
    for check in access_checks:
        blocking_reasons.extend(check.get("reasons", []))
    # De-duplicate while preserving order.
    blocking_reasons = list(dict.fromkeys(blocking_reasons))
    return {
        "mode": "br_exec_02_repository_execution_engine",
        "roadmap_item": {
            "id": "BR-EXEC-02",
            "name": "Repository Execution Engine",
            "status": execution_status,
            "capabilities_delivered": [
                "repository_execution_package",
                "implementation_package_to_edit_operations",
                "branch_intent",
                "commit_intent",
                "pull_request_intent",
                "policy_validation",
                "reviewable_diff_preview",
            ],
        },
        "mission": {
            "goal": goal,
            "requested_by": requested_by,
            "created_at": _now(),
            "founder_approved": founder_approved,
        },
        "repository": {
            "name": repository,
            "base_branch": "main",
            "proposed_branch": branch,
            "direct_main_writes_allowed": False,
            "feature_branch_only": True,
        },
        "credential_status": credential_status,
        "access_checks": access_checks,
        "edit_operations": edits,
        "diff_previews": [
            {"path": edit.get("path"), "diff": _diff_preview(edit), "status": edit.get("status")}
            for edit in edits
        ],
        "execution_intent": {
            "create_branch": can_proceed,
            "apply_file_changes": can_proceed,
            "commit_changes": can_proceed,
            "open_pull_request": can_proceed,
            "auto_merge": False,
            "auto_deploy": False,
            "commit_message": f"BR-EXEC-02 {goal[:72]}",
            "pr_title": f"Mission Control: {goal[:90]}",
            "pr_mode": "draft_until_founder_review",
        },
        "validation_report": {
            "status": "pass" if can_proceed else "blocked",
            "risk_level": _risk_level(edits),
            "blocking_reasons": blocking_reasons,
            "protected_paths_detected": [edit.get("path") for edit in protected_edits],
        },
        "workbench": workbench,
        "audit_trail": [
            {"event": "repository_execution_package_created", "timestamp": _now(), "actor": "repository_execution_engine"},
            {"event": "credential_policy_checked", "timestamp": _now(), "actor": "github_credential_manager"},
            {"event": "protected_path_policy_checked", "timestamp": _now(), "actor": "repository_execution_engine"},
        ],
        "next_action": {
            "owner": "founder" if not can_proceed else "mission_control",
            "action": "Resolve blocking requirements before execution." if not can_proceed else "Proceed to supervised branch/write/PR execution.",
        },
    }


def format_repository_execution_markdown(package: Dict[str, Any]) -> str:
    roadmap = package.get("roadmap_item", {})
    repo = package.get("repository", {})
    validation = package.get("validation_report", {})
    lines = [
        "## BR-EXEC-02 — Repository Execution Engine",
        "",
        f"**Status:** {roadmap.get('status')}",
        f"**Repository:** {repo.get('name')}",
        f"**Branch:** {repo.get('proposed_branch')}",
        f"**Validation:** {validation.get('status')}",
        f"**Risk:** {validation.get('risk_level')}",
        "",
        "### Edit Operations",
    ]
    for edit in package.get("edit_operations", []):
        lines.append(f"- {edit.get('operation')} `{edit.get('path')}` — {edit.get('status')}")
    if validation.get("blocking_reasons"):
        lines.extend(["", "### Blocking Reasons"])
        for reason in validation.get("blocking_reasons", []):
            lines.append(f"- {reason}")
    lines.extend(["", "### Roadmap Capabilities Delivered"])
    for capability in roadmap.get("capabilities_delivered", []):
        lines.append(f"- {capability}")
    return "\n".join(lines)
