from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.platform.guards.filesystem_write_guard import validate_generated_file_write_path
from app.platform.persistence.models import PlatformGeneratedFile
from app.platform.services.materialization_sandbox_writer_service import _safe_workspace_root


STATIC_BROWSER_ENTRY_SUFFIXES = {".html", ".htm"}


def prepare_manual_browser_test_harness(
    db: Session,
    generated_file_id: str,
) -> Dict[str, Any]:
    generated_file = (
        db.query(PlatformGeneratedFile)
        .filter(PlatformGeneratedFile.generated_file_id == generated_file_id)
        .first()
    )

    base = {
        "success": True,
        "generated_file_id": generated_file_id,
        "safety_mode": "manual_browser_test_harness_static_only",
        "manual_test_enabled": False,
        "manual_open_required": True,
        "server_start_performed": False,
        "runtime_server_started": False,
        "preview_server_started": False,
        "generated_code_execution_performed": False,
        "filesystem_write_performed": False,
        "disk_write_performed": False,
        "generated_files_written_to_disk": False,
        "repair_applied": False,
        "restore_executed": False,
        "npm_install_performed": False,
        "node_command_executed": False,
        "python_command_executed": False,
    }

    if not generated_file:
        return {
            **base,
            "found": False,
            "harness_status": "blocked",
            "block_reason": "Generated file was not found in DB preview storage.",
            "workspace_root": None,
            "target_path": None,
            "manual_browser_url": None,
            "instructions": [],
        }

    workspace_root = _safe_workspace_root(generated_file.workspace_id)
    guard_result = validate_generated_file_write_path(
        workspace_root,
        generated_file.path,
    )

    target_path = guard_result.get("resolved_target_path")
    suffix = Path(generated_file.path or "").suffix.lower()

    common = {
        **base,
        "found": True,
        "workflow_run_id": generated_file.workflow_run_id,
        "workspace_id": generated_file.workspace_id,
        "project_id": generated_file.project_id,
        "selected_path": generated_file.path,
        "workspace_root": workspace_root,
        "path_guard": guard_result,
        "target_path": target_path,
        "static_entry_suffix": suffix,
    }

    if not guard_result.get("allowed"):
        return {
            **common,
            "harness_status": "blocked",
            "block_reason": guard_result.get("reason") or "Sandbox path guard blocked this file.",
            "manual_browser_url": None,
            "instructions": [],
        }

    if suffix not in STATIC_BROWSER_ENTRY_SUFFIXES:
        return {
            **common,
            "harness_status": "blocked",
            "block_reason": "Manual browser harness only supports static HTML entry files in V65.",
            "manual_browser_url": None,
            "instructions": [
                "Select a sandbox-written .html or .htm generated file.",
                "Backend files and scripts are intentionally blocked in V65.",
            ],
        }

    resolved_target = Path(str(target_path)).resolve(strict=False)
    if not resolved_target.exists():
        return {
            **common,
            "harness_status": "blocked",
            "block_reason": "Sandbox file does not exist yet. Run approved local sandbox materialization first.",
            "manual_browser_url": None,
            "instructions": [
                "Create or select a persistent materialization approval record.",
                "Run the local sandbox materialization step for this generated file.",
                "Re-run the manual browser test harness after the file exists in the sandbox.",
            ],
        }

    if not resolved_target.is_file():
        return {
            **common,
            "harness_status": "blocked",
            "block_reason": "Sandbox target is not a file.",
            "manual_browser_url": None,
            "instructions": [],
        }

    manual_browser_url = resolved_target.as_uri()

    return {
        **common,
        "harness_status": "ready_for_manual_open",
        "block_reason": None,
        "manual_test_enabled": True,
        "manual_browser_url": manual_browser_url,
        "instructions": [
            "Copy the manual_browser_url into a browser address bar.",
            "Inspect the static generated app manually.",
            "Do not run package installers or generated backend servers in V65.",
        ],
        "message": (
            "Manual browser test harness is ready for a static sandbox file. "
            "No generated code was executed and no server was started."
        ),
    }
