from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.platform.persistence.models import PlatformGeneratedFile
from app.platform.services.controlled_runtime_commands import (
    ALLOWED_RUN_COMMANDS,
    runtime_command,
)
from app.platform.services.materialization_sandbox_writer_service import APPROVED_SANDBOX_ROOT_BASE
from app.platform.services.runtime_approval_gate_service import get_latest_runtime_approval_for_workflow
from app.platform.services.runtime_run_plan_builder_service import build_runtime_run_plan_for_workflow


HOSTED_SANDBOX_BOUNDARY_SAFETY_MODE = "hosted_sandbox_boundary_v85_contract_only"
_SUPPORTED_HOSTED_PROVIDERS = {"fly", "render", "local_only"}


def _safe_flags() -> Dict[str, bool]:
    return {
        "contract_only": True,
        "hosted_execution_enabled": False,
        "hosted_provider_configured": False,
        "hosted_sandbox_started": False,
        "container_started": False,
        "docker_started": False,
        "kubernetes_started": False,
        "deployment_performed": False,
        "public_url_created": False,
        "generated_code_execution_performed": False,
        "runtime_server_started": False,
        "preview_server_started": False,
        "generated_files_written": False,
        "filesystem_write_performed": False,
        "approval_bypass_performed": False,
        "repair_applied": False,
        "restore_executed": False,
        "module_rollout_performed": False,
    }


def _blocked(reason: str, *, workflow_run_id: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "success": True,
        "workflow_run_id": workflow_run_id,
        "hosted_sandbox_status": "blocked_contract_only",
        "block_reason": reason,
        "safety_mode": HOSTED_SANDBOX_BOUNDARY_SAFETY_MODE,
        "details": details or {},
        "safety_flags": _safe_flags(),
    }


def _provider_name() -> str:
    return (os.getenv("HOSTED_SANDBOX_PROVIDER") or "local_only").strip().lower() or "local_only"


def _provider_configured(provider: str) -> bool:
    if provider == "fly":
        return bool(os.getenv("FLY_APP_NAME") and os.getenv("FLY_API_TOKEN"))
    if provider == "render":
        return bool(os.getenv("RENDER_SERVICE_ID") and os.getenv("RENDER_API_KEY"))
    return False


def _first_generated_file(db: Session, workflow_run_id: str) -> Optional[PlatformGeneratedFile]:
    return (
        db.query(PlatformGeneratedFile)
        .filter(PlatformGeneratedFile.workflow_run_id == workflow_run_id)
        .order_by(PlatformGeneratedFile.created_at.asc())
        .first()
    )


def _safe_workspace_name(workspace_id: str) -> str:
    safe = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in workspace_id or "unknown-workspace").strip("-")
    return safe or "unknown-workspace"


def _workspace_root_for_workflow(db: Session, workflow_run_id: str) -> Optional[Path]:
    generated_file = _first_generated_file(db, workflow_run_id)
    if not generated_file or not generated_file.workspace_id:
        return None
    return (APPROVED_SANDBOX_ROOT_BASE / _safe_workspace_name(generated_file.workspace_id)).resolve()


def _working_directory_status(workspace_root: Optional[Path], run_plan: Dict[str, Any]) -> Dict[str, Any]:
    if workspace_root is None:
        return {"ok": False, "reason": "workspace_root_missing", "working_directory": None}
    working_directory = (run_plan.get("working_directory") or ".").strip() or "."
    candidate = (workspace_root / working_directory).resolve()
    try:
        candidate.relative_to(workspace_root.resolve())
    except ValueError:
        return {
            "ok": False,
            "reason": "working_directory_escapes_workspace_root",
            "working_directory": str(candidate),
        }
    return {
        "ok": True,
        "reason": None,
        "working_directory": str(candidate),
        "exists": candidate.exists(),
    }


def inspect_hosted_sandbox_boundary(db: Session, *, workflow_run_id: str) -> Dict[str, Any]:
    """Inspect hosted sandbox eligibility without creating hosted infrastructure."""
    provider = _provider_name()
    provider_supported = provider in _SUPPORTED_HOSTED_PROVIDERS
    provider_configured = _provider_configured(provider)

    generated_file = _first_generated_file(db, workflow_run_id)
    generated_file_found = generated_file is not None
    workspace_id = generated_file.workspace_id if generated_file else None
    workspace_root = _workspace_root_for_workflow(db, workflow_run_id)

    run_plan_result = build_runtime_run_plan_for_workflow(db, workflow_run_id=workflow_run_id)
    run_plan = run_plan_result.get("runtime_run_plan") or {}
    run_command = runtime_command(run_plan) if run_plan else None
    run_command_allowed = run_command in ALLOWED_RUN_COMMANDS if run_command else False
    working_directory = _working_directory_status(workspace_root, run_plan)
    approval_result = get_latest_runtime_approval_for_workflow(db, workflow_run_id=workflow_run_id)
    approval_record = approval_result.get("approval_record") or {}
    runtime_approved = bool(approval_result.get("found") and approval_record.get("approval_status") == "approved")

    checks = {
        "provider_name_supported": provider_supported,
        "provider_configured": False,
        "generated_file_found": generated_file_found,
        "workspace_id_found": bool(workspace_id),
        "workspace_root_resolved": workspace_root is not None,
        "workspace_root_inside_approved_base": (
            str(workspace_root).startswith(str(APPROVED_SANDBOX_ROOT_BASE.resolve()))
            if workspace_root else False
        ),
        "run_plan_available": bool(run_plan_result.get("found")),
        "run_command_allowed": run_command_allowed,
        "working_directory_inside_workspace_root": bool(working_directory.get("ok")),
        "runtime_approval_checked": True,
        "runtime_approved": runtime_approved,
        "hosted_execution_blocked_by_contract": True,
    }

    details = {
        "provider": provider,
        "provider_supported": provider_supported,
        "provider_configured_actual": provider_configured,
        "workflow_run_id": workflow_run_id,
        "workspace_id": workspace_id,
        "workspace_root": str(workspace_root) if workspace_root else None,
        "approved_sandbox_root_base": str(APPROVED_SANDBOX_ROOT_BASE.resolve()),
        "run_plan_found": bool(run_plan_result.get("found")),
        "run_command": run_command,
        "allowed_run_commands": sorted(ALLOWED_RUN_COMMANDS),
        "working_directory": working_directory,
        "runtime_approval_found": bool(approval_result.get("found")),
        "runtime_approval_status": approval_record.get("approval_status"),
        "checks": checks,
    }

    return _blocked(
        "Hosted sandbox execution is contract-only in V85 and remains disabled until a later deployment-pack milestone.",
        workflow_run_id=workflow_run_id,
        details=details,
    )
