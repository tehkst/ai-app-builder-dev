from __future__ import annotations

import os
import subprocess
import time
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.platform.services.controlled_runtime_commands import (
    ALLOWED_INSTALL_COMMANDS,
    ALLOWED_RUN_COMMANDS,
    install_command,
    npm_command_args,
    runtime_command,
)
from app.platform.services.controlled_runtime_logs import init_runtime_log_record, start_runtime_log_readers
from app.platform.services.controlled_runtime_registry import RUNNING_PROCESSES
from app.platform.services.controlled_runtime_responses import (
    already_running_response,
    blocked_runtime_response,
    install_failed_response,
    started_response,
)
from app.platform.services.controlled_runtime_workspace import resolve_working_directory, workspace_root_for_workflow
from app.platform.services.materialization_sandbox_writer_service import APPROVED_SANDBOX_ROOT_BASE
from app.platform.services.runtime_approval_gate_service import get_latest_runtime_approval_for_workflow
from app.platform.services.runtime_run_plan_builder_service import build_runtime_run_plan_for_workflow

def _is_approved(approval_result: Dict[str, Any]) -> bool:
    record = approval_result.get("approval_record") or {}
    return bool(approval_result.get("found") and record.get("approval_status") == "approved")


def _install_dependencies(
    workflow_run_id: str,
    working_directory: Path,
    install: str,
) -> Dict[str, Any]:
    install_args = npm_command_args(install)
    if not install_args:
        return {"ok": False, "reason": "Install command could not be translated into safe argv."}
    completed = subprocess.run(
        install_args,
        cwd=str(working_directory),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    result = {
        "command": install,
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
    }
    if completed.returncode != 0:
        return {
            "ok": False,
            "reason": "Install command failed; runtime was not started.",
            "install_result": result,
        }
    return {"ok": True, "install_result": result}


def start_controlled_sandbox_runtime_for_workflow(
    db: Session,
    workflow_run_id: str,
    *,
    perform_install: bool = False,
) -> Dict[str, Any]:
    process = RUNNING_PROCESSES.get(workflow_run_id)
    if process and process.poll() is None:
        return already_running_response(workflow_run_id, process)

    run_plan_result = build_runtime_run_plan_for_workflow(db, workflow_run_id=workflow_run_id)
    if not run_plan_result.get("found"):
        return blocked_runtime_response(workflow_run_id, "Runtime run plan was not found.", run_plan_result=run_plan_result)

    run_plan = run_plan_result.get("runtime_run_plan") or {}
    if run_plan.get("status") != "runtime_run_plan_ready_for_approval":
        return blocked_runtime_response(workflow_run_id, "Runtime run plan is not ready for approval-controlled execution.", run_plan_result=run_plan_result)

    approval_result = get_latest_runtime_approval_for_workflow(db, workflow_run_id=workflow_run_id)
    if not _is_approved(approval_result):
        return blocked_runtime_response(workflow_run_id, "Latest runtime approval record is required and must be approved.", run_plan_result=run_plan_result, approval_result=approval_result)

    workspace_root = workspace_root_for_workflow(db, workflow_run_id)
    if not workspace_root:
        return blocked_runtime_response(workflow_run_id, "Workspace root could not be resolved from generated files.", run_plan_result=run_plan_result, approval_result=approval_result)
    workspace_root = workspace_root.resolve()
    if not str(workspace_root).startswith(str(APPROVED_SANDBOX_ROOT_BASE.resolve())):
        return blocked_runtime_response(workflow_run_id, "Workspace root is outside the approved sandbox base.", run_plan_result=run_plan_result, approval_result=approval_result, workspace_root=str(workspace_root))

    working_directory = resolve_working_directory(workspace_root, run_plan)
    if not working_directory or not working_directory.exists():
        reason = "Run plan working directory escapes the approved sandbox root." if not working_directory else "Run plan working directory does not exist in the sandbox. Materialize approved files first."
        return blocked_runtime_response(workflow_run_id, reason, run_plan_result=run_plan_result, approval_result=approval_result, workspace_root=str(workspace_root), working_directory=str(working_directory or run_plan.get("working_directory")))

    install = install_command(run_plan)
    if install and install not in ALLOWED_INSTALL_COMMANDS:
        return blocked_runtime_response(workflow_run_id, "Install command is not in the V70 allowlist.", run_plan_result=run_plan_result, approval_result=approval_result, workspace_root=str(workspace_root), working_directory=str(working_directory))

    run = runtime_command(run_plan)
    if run not in ALLOWED_RUN_COMMANDS:
        return blocked_runtime_response(workflow_run_id, "Run command is not in the V70 allowlist.", run_plan_result=run_plan_result, approval_result=approval_result, workspace_root=str(workspace_root), working_directory=str(working_directory))

    install_result = None
    if perform_install:
        install_check = _install_dependencies(workflow_run_id, working_directory, install or "")
        install_result = install_check.get("install_result")
        if not install_check.get("ok"):
            return install_failed_response(workflow_run_id, workspace_root, working_directory, run_plan, approval_result, install_result or {})

    run_args = npm_command_args(run or "")
    if not run_args:
        return blocked_runtime_response(workflow_run_id, "Run command could not be translated into safe argv.", run_plan_result=run_plan_result, approval_result=approval_result, workspace_root=str(workspace_root), working_directory=str(working_directory))

    env = os.environ.copy()
    env.setdefault("HOST", "127.0.0.1")
    env.setdefault("PORT", str(run_plan.get("port") or 5173))
    process = subprocess.Popen(run_args, cwd=str(working_directory), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True, env=env)
    RUNNING_PROCESSES[workflow_run_id] = process
    init_runtime_log_record(workflow_run_id, process, run or "", run_args)
    start_runtime_log_readers(workflow_run_id, process)
    time.sleep(1)
    return started_response(workflow_run_id, process, workspace_root, working_directory, install_result, run_plan, approval_result, run, run_args)
