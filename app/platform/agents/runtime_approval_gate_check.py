import json
import uuid

from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import PlatformGeneratedFile
from app.platform.services.runtime_approval_gate_service import (
    approve_runtime_run_plan_for_workflow,
    get_latest_runtime_approval_for_workflow,
    reject_runtime_run_plan_for_workflow,
)
from app.platform.services.runtime_run_plan_builder_service import build_runtime_run_plan_for_workflow


def _create_generated_file(db, generated_file_id, workflow_run_id, workspace_id, path, language, content):
    generated_file = PlatformGeneratedFile(
        generated_file_id=generated_file_id,
        workflow_run_id=workflow_run_id,
        workspace_id=workspace_id,
        project_id="v69-runtime-approval-gate-project",
        source_step_id="v69-check-step",
        source_agent_id="v69-check-agent",
        path=path,
        language=language,
        purpose="V69 runtime approval gate smoke check",
        content_preview=content,
        content_hash=f"v69-check-content-hash-{generated_file_id}",
        write_status="persisted_preview",
        rollback_status="not_required",
        metadata_json="{}",
    )
    db.add(generated_file)
    db.commit()
    return generated_file


def _safe_flags(result):
    return result.get("safety_flags") or {}


def run_check() -> dict:
    create_platform_tables()
    db = PlatformSessionLocal()

    run_token = uuid.uuid4().hex
    workflow_run_id = f"v69-runtime-approval-gate-check-run-{run_token}"
    workspace_id = f"v69-runtime-approval-gate-workspace-{run_token}"

    try:
        _create_generated_file(
            db,
            generated_file_id=f"v69-package-json-{run_token}",
            workflow_run_id=workflow_run_id,
            workspace_id=workspace_id,
            path="frontend/package.json",
            language="json",
            content=json.dumps(
                {
                    "scripts": {"dev": "vite --host 0.0.0.0", "build": "vite build"},
                    "dependencies": {"vite": "latest", "react": "latest"},
                }
            ),
        )
        _create_generated_file(
            db,
            generated_file_id=f"v69-index-html-{run_token}",
            workflow_run_id=workflow_run_id,
            workspace_id=workspace_id,
            path="frontend/index.html",
            language="html",
            content="<div id='root'></div><script type='module' src='/src/main.jsx'></script>",
        )
        _create_generated_file(
            db,
            generated_file_id=f"v69-main-jsx-{run_token}",
            workflow_run_id=workflow_run_id,
            workspace_id=workspace_id,
            path="frontend/src/main.jsx",
            language="javascript",
            content="console.log(import.meta.env.VITE_API_URL);",
        )

        run_plan = build_runtime_run_plan_for_workflow(db, workflow_run_id=workflow_run_id)
        approved = approve_runtime_run_plan_for_workflow(
            db,
            workflow_run_id=workflow_run_id,
            approved_by="v69-smoke-check",
            approval_reason="Smoke check approval record only.",
        )
        rejected = reject_runtime_run_plan_for_workflow(
            db,
            workflow_run_id=workflow_run_id,
            approved_by="v69-smoke-check",
            approval_reason="Smoke check rejection record only.",
        )
        latest = get_latest_runtime_approval_for_workflow(db, workflow_run_id=workflow_run_id)

        approval_record = approved.get("approval_record") or {}
        rejection_record = rejected.get("approval_record") or {}
        latest_record = latest.get("approval_record") or {}
        approval_safety = _safe_flags(approved)
        rejection_safety = _safe_flags(rejected)
        latest_safety = _safe_flags(latest)

        checks = {
            "run_plan_ready": (run_plan.get("runtime_run_plan") or {}).get("status") == "runtime_run_plan_ready_for_approval",
            "approval_record_created": approved.get("record_created") is True,
            "approval_status_approved": approval_record.get("approval_status") == "approved",
            "approval_action_approve": approval_record.get("approval_action") == "approve",
            "approval_runtime_disabled": approval_record.get("runtime_execution_enabled") is False,
            "rejection_record_created": rejected.get("record_created") is True,
            "rejection_status_rejected": rejection_record.get("approval_status") == "rejected",
            "rejection_action_reject": rejection_record.get("approval_action") == "reject",
            "latest_found": latest.get("found") is True,
            "latest_is_rejection": latest_record.get("approval_status") == "rejected",
            "framework_type_vite_react": approval_record.get("framework_type") == "vite_react",
            "working_directory_frontend": approval_record.get("working_directory") == "frontend",
            "install_command_planned_only": approval_record.get("install_command") == "npm install",
            "run_command_planned_only": approval_record.get("run_command") == "npm run dev",
            "runtime_port_vite": approval_record.get("runtime_port") == 5173,
            "approval_gate_only": approval_safety.get("approval_gate_only") is True,
            "rejection_gate_only": rejection_safety.get("approval_gate_only") is True,
            "latest_gate_only": latest_safety.get("approval_gate_only") is True,
            "no_install": approval_safety.get("install_packages_performed") is False,
            "no_runtime_server": approval_safety.get("runtime_server_started") is False,
            "no_preview_server": approval_safety.get("preview_server_started") is False,
            "no_generated_code_execution": approval_safety.get("generated_code_execution_performed") is False,
            "no_node_command": approval_safety.get("node_command_executed") is False,
            "no_python_command": approval_safety.get("python_command_executed") is False,
            "no_generated_files_written": approval_safety.get("generated_files_written") is False,
            "no_filesystem_write": approval_safety.get("filesystem_write_performed") is False,
            "no_disk_write": approval_safety.get("disk_write_performed") is False,
            "no_repair_applied": approval_safety.get("repair_applied") is False,
            "no_restore_executed": approval_safety.get("restore_executed") is False,
        }

        return {
            "check": "runtime_approval_gate_check",
            "passed": all(checks.values()),
            "checks": checks,
            "sample": {
                "run_plan": run_plan,
                "approved": approved,
                "rejected": rejected,
                "latest": latest,
            },
        }
    finally:
        db.close()


if __name__ == "__main__":
    result = run_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)
