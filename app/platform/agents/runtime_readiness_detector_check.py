import json
import uuid

from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import PlatformGeneratedFile
from app.platform.services.runtime_readiness_detector_service import (
    detect_runtime_readiness_for_workflow,
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
        project_id="v67-runtime-readiness-detector-project",
        source_step_id="v67-check-step",
        source_agent_id="v67-check-agent",
        path=path,
        language=language,
        purpose="V67 runtime readiness detector smoke check",
        content_preview=content,
        content_hash=f"v67-check-content-hash-{generated_file_id}",
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
    workflow_run_id = f"v67-runtime-readiness-check-run-{run_token}"
    workspace_id = f"v67-runtime-readiness-workspace-{run_token}"

    try:
        _create_generated_file(
            db,
            generated_file_id=f"v67-package-json-{run_token}",
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
            generated_file_id=f"v67-index-html-{run_token}",
            workflow_run_id=workflow_run_id,
            workspace_id=workspace_id,
            path="frontend/index.html",
            language="html",
            content="<div id='root'></div><script type='module' src='/src/main.jsx'></script>",
        )

        _create_generated_file(
            db,
            generated_file_id=f"v67-main-jsx-{run_token}",
            workflow_run_id=workflow_run_id,
            workspace_id=workspace_id,
            path="frontend/src/main.jsx",
            language="javascript",
            content="console.log(import.meta.env.VITE_API_URL);",
        )

        result = detect_runtime_readiness_for_workflow(
            db,
            workflow_run_id=workflow_run_id,
        )

        readiness = result.get("runtime_readiness") or {}
        safety = result.get("safety_flags") or {}

        checks = {
            "success": result.get("success") is True,
            "found": result.get("found") is True,
            "framework_type_vite_react": readiness.get("framework_type") == "vite_react",
            "package_manager_npm": readiness.get("package_manager") == "npm",
            "install_command_planned_only": readiness.get("likely_install_command") == "npm install",
            "run_command_planned_only": readiness.get("likely_run_command") == "npm run dev",
            "likely_port_vite": readiness.get("likely_port") == 5173,
            "entry_files_detected": "frontend/package.json" in readiness.get("entry_files", []),
            "env_var_hint_detected": "VITE_API_URL" in readiness.get("env_var_hints", []),
            "approval_required": "runtime_start_approval_required_before_future_run" in readiness.get("approval_requirements", []),
            "detection_only": safety.get("detection_only") is True,
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
            "no_repair_applied": safety.get("repair_applied") is False,
            "no_restore_executed": safety.get("restore_executed") is False,
        }

        return {
            "check": "runtime_readiness_detector_check",
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
