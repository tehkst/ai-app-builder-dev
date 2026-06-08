from __future__ import annotations

import hashlib
import uuid
from typing import Any, Dict

from app.platform.persistence.database import PlatformSessionLocal
from app.platform.persistence.models import PlatformGeneratedFile
from app.platform.services.hosted_sandbox_boundary_service import (
    HOSTED_SANDBOX_BOUNDARY_SAFETY_MODE,
    inspect_hosted_sandbox_boundary,
)


def _create_seed_generated_file(db, *, token: str) -> Dict[str, Any]:
    workflow_run_id = f"v85-hosted-sandbox-boundary-check-run-{token}"
    workspace_id = f"v85-hosted-sandbox-boundary-workspace-{token}"
    content_preview = '{"scripts":{"dev":"vite --host 127.0.0.1"},"dependencies":{"@vitejs/plugin-react":"latest","vite":"latest","react":"latest","react-dom":"latest"}}'
    generated_file = PlatformGeneratedFile(
        generated_file_id=f"v85-hosted-sandbox-boundary-file-{token}",
        workflow_run_id=workflow_run_id,
        workspace_id=workspace_id,
        project_id="v85-hosted-sandbox-boundary-project",
        path="package.json",
        content_preview=content_preview,
        content_hash=hashlib.sha256(content_preview.encode("utf-8")).hexdigest(),
        write_status="persisted_preview",
        purpose="V85 hosted sandbox boundary smoke check",
    )
    db.add(generated_file)
    db.commit()
    return {
        "workflow_run_id": workflow_run_id,
        "workspace_id": workspace_id,
        "generated_file_id": generated_file.generated_file_id,
    }


def _safe_flags_preserved(flags: Dict[str, bool]) -> bool:
    return (
        flags.get("contract_only") is True
        and flags.get("hosted_execution_enabled") is False
        and flags.get("hosted_provider_configured") is False
        and flags.get("hosted_sandbox_started") is False
        and flags.get("container_started") is False
        and flags.get("docker_started") is False
        and flags.get("kubernetes_started") is False
        and flags.get("deployment_performed") is False
        and flags.get("public_url_created") is False
        and flags.get("generated_code_execution_performed") is False
        and flags.get("runtime_server_started") is False
        and flags.get("preview_server_started") is False
        and flags.get("generated_files_written") is False
        and flags.get("filesystem_write_performed") is False
        and flags.get("approval_bypass_performed") is False
        and flags.get("repair_applied") is False
        and flags.get("restore_executed") is False
        and flags.get("module_rollout_performed") is False
    )


def run_hosted_sandbox_boundary_check() -> Dict[str, Any]:
    token = uuid.uuid4().hex[:10]
    db = PlatformSessionLocal()
    try:
        seed = _create_seed_generated_file(db, token=token)
        result = inspect_hosted_sandbox_boundary(db, workflow_run_id=seed["workflow_run_id"])
    finally:
        db.close()

    details = result.get("details") or {}
    checks = details.get("checks") or {}
    flags = result.get("safety_flags") or {}

    validation = {
        "contract_only_status": result.get("hosted_sandbox_status") == "blocked_contract_only",
        "expected_safety_mode": result.get("safety_mode") == HOSTED_SANDBOX_BOUNDARY_SAFETY_MODE,
        "generated_file_found": checks.get("generated_file_found") is True,
        "workspace_id_found": checks.get("workspace_id_found") is True,
        "workspace_root_resolved": checks.get("workspace_root_resolved") is True,
        "workspace_root_inside_approved_base": checks.get("workspace_root_inside_approved_base") is True,
        "run_plan_available": checks.get("run_plan_available") is True,
        "run_command_allowed": checks.get("run_command_allowed") is True,
        "working_directory_inside_workspace_root": checks.get("working_directory_inside_workspace_root") is True,
        "runtime_approval_checked": checks.get("runtime_approval_checked") is True,
        "hosted_execution_blocked_by_contract": checks.get("hosted_execution_blocked_by_contract") is True,
        "provider_configuration_not_enabled_for_v85": checks.get("provider_configured") is False,
        "safety_flags_preserved": _safe_flags_preserved(flags),
    }

    passed = all(validation.values())
    return {
        "check": "hosted_sandbox_boundary_check",
        "milestone": "V85 — Hosted Sandbox Boundary",
        "passed": passed,
        "safety_mode": HOSTED_SANDBOX_BOUNDARY_SAFETY_MODE,
        "validation": validation,
        "seed": seed,
        "result": result,
    }


def main() -> int:
    result = run_hosted_sandbox_boundary_check()
    print(result)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
