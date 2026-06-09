from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from app.platform.services.generated_preview_repair_proposal_service import (
    generate_generated_preview_repair_proposal,
)


V93_SAFETY_MODE = "generated_preview_repair_apply_v93_approval_gated"


@dataclass(frozen=True)
class GeneratedPreviewRepairApproval:
    approved: bool
    approved_by: str
    approval_reason: str


def _base_flags() -> Dict[str, bool]:
    return {
        "repair_apply_requires_approval": True,
        "approval_bypass_performed": False,
        "db_content_mutation_performed": False,
        "generated_code_execution_performed": False,
        "runtime_server_started": False,
        "preview_server_started": False,
        "external_deployment_performed": False,
    }


def _blocked_result(
    *,
    workflow_run_id: str | None,
    selected_path: str | None,
    reason: str,
    proposal: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return {
        "success": True,
        "milestone": "V93",
        "workflow_run_id": workflow_run_id,
        "selected_path": selected_path,
        "safety_mode": V93_SAFETY_MODE,
        "repair_apply_status": "blocked",
        "block_reason": reason,
        "repair_actions_applied": False,
        "filesystem_write_performed": False,
        "disk_write_performed": False,
        "generated_files_written_to_disk": False,
        "target_exists_after_apply": False,
        "target_under_workspace_after_apply": False,
        "proposal": proposal,
        **_base_flags(),
    }


def approve_generated_preview_repair(
    *,
    approved_by: str,
    approval_reason: str,
) -> Dict[str, Any]:
    return {
        "success": True,
        "milestone": "V93",
        "approval_status": "approved",
        "approved": True,
        "approved_by": approved_by,
        "approval_reason": approval_reason,
        "safety_mode": V93_SAFETY_MODE,
        "approval_bypass_performed": False,
        "repair_apply_requires_approval": True,
    }


def _safe_target_path(workspace_root: str, target_file: str) -> Path:
    root = Path(workspace_root).resolve()
    target = (root / target_file).resolve()
    if not str(target).startswith(str(root)):
        raise ValueError(f"Repair target escapes workspace root: {target_file}")
    return target


def apply_generated_preview_repair(
    *,
    workflow_run_id: str | None,
    selected_path: str | None,
    diagnostics: Dict[str, Any],
    workspace_root: str,
    approval: Dict[str, Any] | None,
) -> Dict[str, Any]:
    proposal = generate_generated_preview_repair_proposal(
        workflow_run_id=workflow_run_id,
        selected_path=selected_path,
        diagnostics=diagnostics,
    )

    if not approval or approval.get("approved") is not True:
        return _blocked_result(
            workflow_run_id=workflow_run_id,
            selected_path=selected_path,
            reason="Explicit generated preview repair approval is required before apply.",
            proposal=proposal,
        )

    proposal_items = (proposal.get("repair_proposal") or {}).get("proposal_items") or []
    missing_asset_item = next(
        (item for item in proposal_items if item.get("issue_kind") == "missing_linked_static_asset"),
        None,
    )

    if not missing_asset_item:
        return _blocked_result(
            workflow_run_id=workflow_run_id,
            selected_path=selected_path,
            reason="No supported generated preview repair action was found in the proposal.",
            proposal=proposal,
        )

    target_file = str(missing_asset_item.get("target_file") or "")
    if not target_file:
        return _blocked_result(
            workflow_run_id=workflow_run_id,
            selected_path=selected_path,
            reason="Repair proposal did not include a target file.",
            proposal=proposal,
        )

    try:
        target_path = _safe_target_path(workspace_root, target_file)
    except ValueError as exc:
        return _blocked_result(
            workflow_run_id=workflow_run_id,
            selected_path=selected_path,
            reason=str(exc),
            proposal=proposal,
        )

    target_path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        "/* V93 approved generated preview repair */\n"
        "/* Missing linked static asset recreated for static preview re-test only. */\n"
        ":root { --v93-repair-applied: 1; }\n"
    )
    target_path.write_text(content, encoding="utf-8")

    target_exists = target_path.exists()
    target_under_workspace = str(target_path.resolve()).startswith(str(Path(workspace_root).resolve()))

    return {
        "success": True,
        "milestone": "V93",
        "workflow_run_id": workflow_run_id,
        "selected_path": selected_path,
        "safety_mode": V93_SAFETY_MODE,
        "repair_apply_status": "applied",
        "repair_actions_applied": True,
        "applied_repair_kind": "missing_linked_static_asset",
        "target_file": target_file,
        "target_path": str(target_path),
        "target_exists_after_apply": target_exists,
        "target_under_workspace_after_apply": target_under_workspace,
        "filesystem_write_performed": True,
        "disk_write_performed": True,
        "generated_files_written_to_disk": True,
        "proposal": proposal,
        "approval": approval,
        **_base_flags(),
    }


def retest_generated_preview_repair(
    *,
    target_path: str,
    workspace_root: str,
) -> Dict[str, Any]:
    target = Path(target_path).resolve()
    root = Path(workspace_root).resolve()
    target_exists = target.exists()
    target_under_workspace = str(target).startswith(str(root))

    return {
        "success": target_exists and target_under_workspace,
        "milestone": "V93",
        "safety_mode": V93_SAFETY_MODE,
        "retest_status": "passed" if target_exists and target_under_workspace else "failed",
        "target_path": str(target),
        "workspace_root": str(root),
        "target_exists": target_exists,
        "target_under_workspace": target_under_workspace,
        "read_only_retest": True,
        "repair_actions_applied": False,
        "filesystem_write_performed": False,
        "disk_write_performed": False,
        "generated_files_written_to_disk": False,
        **_base_flags(),
    }
