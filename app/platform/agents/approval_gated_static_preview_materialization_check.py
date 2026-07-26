from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from app.platform.agents.app_build_request_run_check import run_app_build_request
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.services.customer_app_scope_service import draft_and_approve_customer_app_scope
from app.platform.services.materialization_approval_record_service import (
    create_materialization_approval_record,
)
from app.platform.services.materialization_dry_run_service import build_materialization_dry_run
from app.platform.services.materialization_execution_gate_service import (
    attempt_materialization_execution,
)


def run_check(app_request: str, real_bridge: bool = True) -> Dict[str, Any]:
    create_platform_tables()
    scope_db = PlatformSessionLocal()
    try:
        scope = draft_and_approve_customer_app_scope(
            scope_db,
            app_request=app_request,
            requested_by="v90_smoke_check",
        )
    finally:
        scope_db.close()

    build_result = run_app_build_request(
        app_request=app_request,
        scoping_request_id=scope["scoping_request_id"],
        real_bridge=real_bridge,
    )
    summary = build_result.get("summary") or {}
    persistence = summary.get("generated_file_persistence") or {}
    generated_files = persistence.get("generated_files") or []

    selected_file = next(
        (file for file in generated_files if file.get("path") == "index.html"),
        generated_files[0] if generated_files else None,
    )
    if not selected_file:
        return {"success": False, "reason": "no_generated_file_available", "build_result": build_result}

    generated_file_id = str(selected_file.get("generated_file_id"))

    db = PlatformSessionLocal()
    try:
        dry_run = build_materialization_dry_run(db, generated_file_id=generated_file_id)
        blocked = attempt_materialization_execution(db, generated_file_id=generated_file_id)
        approval = create_materialization_approval_record(
            db,
            generated_file_id=generated_file_id,
            approved_by="v90_smoke_check",
            approval_reason="V90 approval-gated static preview materialization smoke check.",
        )
        materialized = attempt_materialization_execution(db, generated_file_id=generated_file_id)
    finally:
        db.close()

    materialization_result = materialized.get("materialization_result") or {}
    target_path = materialization_result.get("target_path")
    workspace_root = materialization_result.get("workspace_root")

    target_exists = bool(target_path and Path(target_path).exists())
    target_under_workspace = False
    if target_path and workspace_root:
        target_under_workspace = str(Path(target_path).resolve()).startswith(
            str(Path(workspace_root).resolve())
        )

    checks = {
        "build_success": build_result.get("success") is True,
        "generated_file_count_ok": summary.get("generated_file_count", 0) >= 4,
        "dry_run_only": dry_run.get("dry_run_only") is True,
        "dry_run_no_write": dry_run.get("filesystem_write_performed") is False
        and dry_run.get("disk_write_performed") is False,
        "blocked_before_approval": blocked.get("execution_gate_status") == "blocked"
        and blocked.get("materialization_execution_performed") is False,
        "approval_grants_static_materialization": approval.get("approval_grants_filesystem_write_capability") is True
        and approval.get("materialization_execution_enabled") is True,
        "materialized_after_approval": materialized.get("materialization_execution_performed") is True,
        "target_exists": target_exists,
        "target_under_workspace": target_under_workspace,
        "no_generated_code_execution": materialized.get("generated_code_execution_performed") is False,
        "no_runtime_server": materialized.get("runtime_server_started") is False,
        "no_preview_server": materialized.get("preview_server_started") is False,
        "no_external_deployment": materialized.get("external_deployment_performed") is False,
    }

    return {
        "success": all(checks.values()),
        "milestone": "V90",
        "app_request": app_request,
        "workflow_run_id": summary.get("workflow_run_id"),
        "generated_file_count": summary.get("generated_file_count"),
        "selected_generated_file_id": generated_file_id,
        "selected_path": selected_file.get("path"),
        "dry_run": dry_run,
        "blocked_before_approval": blocked,
        "approval": approval,
        "materialization": materialized,
        "checks": checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="V90 approval-gated static preview materialization smoke check.")
    parser.add_argument("app_request", nargs="?", default="Build me a simple booking app for yoga classes")
    parser.add_argument("--simulation", action="store_true")
    args = parser.parse_args()

    result = run_check(args.app_request, real_bridge=not args.simulation)
    print(json.dumps(result, indent=2, sort_keys=True))

    if not result.get("success"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
