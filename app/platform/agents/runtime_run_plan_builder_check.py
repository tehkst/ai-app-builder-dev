import json
import uuid

from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import PlatformGeneratedFile
from app.platform.services.runtime_run_plan_builder_service import (
    build_runtime_run_plan_for_workflow,
)


def _create_generated_file(
    db,
    generated_file_id: str,
    workflow_run_id: str,
    workspace_id: str,
    path: str,
    language: str,
    content: str,
) -> PlatformGeneratedFile:
    generated_file = PlatformGeneratedFile(
        generated_file_id=generated_file_id,
        workflow_run_id=workflow_run_id,
        workspace_id=workspace_id,
        project_id="v68-runtime-run-plan-builder-project",
        source_step_id="v68-check-step",
        source_agent_id="v68-check-agent",
        path=path,
        language=language,
        purpose="V68 runtime run plan builder smoke check",
        content_preview=content,
        content_hash=f"v68-check-content-hash-{generated_file_id}",
        write_status="persisted_preview",
        rollback_status="not_required",
        metadata_json="{}",
    )
    db.add(generated_file)
    db.commit()
    return generated_file


def run_check() -> dict:
    create_platform_tables()
    db = PlatformSessionLocal()

    run_token = uuid.uuid4().hex
    workflow_run_id = f"v68-runtime-run-plan-check-run-{run_token}"
    workspace_id = f"v68-runtime-run-plan-workspace-{run_token}"

    try:
        _create_generated_file(
            db,
            generated_file_id=f"v68-package-json-{run_token}",
            workflow_run_id=workflow_run_id,
            workspace_id=workspace_id,
            path="frontend/package.json",
            language="json",
            content=json.dumps(
                {
                    "scripts": {"dev": "vite --host 0.0.0.0", "build": "vite build"},
                    "dependencies": {
                        "@vitejs/plugin-react": "latest",
                        "vite": "latest",
                        "react": "latest",
                    },
                }
            ),
        )

        _create_generated_file(
            db,
            generated_file_id=f"v68-index-html-{run_token}",
            workflow_run_id=workflow_run_id,
            workspace_id=workspace_id,
            path="frontend/index.html",
            language="html",
            content="<div id='root'></div><script type='module' src='/src/main.jsx'></script>",
        )

        _create_generated_file(
            db,
            generated_file_id=f"v68-main-jsx-{run_token}",
            workflow_run_id=workflow_run_id,
            workspace_id=workspace_id,
            path="frontend/src/main.jsx",
            language="javascript",
            content="console.log(import.meta.env.VITE_API_URL);",
        )

        result = build_runtime_run_plan_for_workflow(
            db,
            workflow_run_id=workflow_run_id,
        )

        plan = result.get("runtime_run_plan") or {}
        install_step = plan.get("install_step") or {}
        run_step = plan.get("run_step") or {}
        safety = result.get("safety_flags") or {}

        checks = {
            "success": result.get("success") is True,
            "found": result.get("found") is True,
            "plan_ready": plan.get("status") == "runtime_run_plan_ready_for_approval",
            "framework_type_vite_react": plan.get("framework_type") == "vite_react",
            "working_directory_frontend": plan.get("working_directory") == "frontend",
            "package_manager_npm": plan.get("package_manager") == "npm",
            "install_step_required": install_step.get("required") is True,
            "install_command_planned_only": install_step.get("command") == "npm install",
            "install_step_not_performed": install_step.get("performed") is False,
            "run_step_required": run_step.get("required") is True,
            "run_command_planned_only": run_step.get("command") == "npm run dev",
            "run_step_not_performed": run_step.get("performed") is False,
            "likely_port_vite": plan.get("port") == 5173,
            "env_requirement_detected": "VITE_API_URL" in plan.get("env_requirements", []),
            "approval_required": "runtime_run_plan_review_required" in plan.get("approval_requirements", []),
            "no_blocking_reasons": plan.get("blocking_reasons") == [],
            "plan_only": safety.get("plan_only") is True,
            "no_install": safety.get("install_packages_performed") is False,
            "no_npm_install": safety.get("npm_install_performed") is False,
            "no_pip_install": safety.get("pip_install_performed") is False,
            "no_runtime_server": safety.get("runtime_server_started") is False,
            "no_preview_server": safety.get("preview_server_started") is False,
            "no_server_start": safety.get("server_start_performed") is False,
            "no_generated_code_execution": safety.get("generated_code_execution_performed") is False,
            "no_node_command": safety.get("node_command_executed") is False,
            "no_python_command": safety.get("python_command_executed") is False,
            "no_filesystem_write": safety.get("filesystem_write_performed") is False,
            "no_disk_write": safety.get("disk_write_performed") is False,
            "no_generated_files_written": safety.get("generated_files_written") is False,
            "no_repair_applied": safety.get("repair_applied") is False,
            "no_restore_executed": safety.get("restore_executed") is False,
        }

        return {
            "check": "runtime_run_plan_builder_check",
            "passed": all(checks.values()),
            "checks": checks,
            "sample": result,
        }
    finally:
        db.close()


if __name__ == "__main__":
    result = run_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)
