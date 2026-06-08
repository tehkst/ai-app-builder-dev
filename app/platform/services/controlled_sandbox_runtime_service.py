from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.platform.persistence.models import PlatformGeneratedFile
from app.platform.services.materialization_sandbox_writer_service import APPROVED_SANDBOX_ROOT_BASE
from app.platform.services.runtime_approval_gate_service import get_latest_runtime_approval_for_workflow
from app.platform.services.runtime_run_plan_builder_service import build_runtime_run_plan_for_workflow


CONTROLLED_SANDBOX_RUNTIME_SAFETY_MODE = "controlled_sandbox_runtime_v70_approved_sandbox_only"
_ALLOWED_RUN_COMMANDS = {"npm run dev"}
_ALLOWED_INSTALL_COMMANDS = {"npm install"}
_RUNNING_PROCESSES: Dict[str, subprocess.Popen] = {}


def _safe_flags(
    *,
    runtime_started: bool = False,
    install_performed: bool = False,
    node_command_executed: bool = False,
) -> Dict[str, bool]:
    return {
        "controlled_sandbox_runtime": True,
        "approval_gate_checked": True,
        "sandbox_boundary_checked": True,
        "runtime_execution_enabled": runtime_started,
        "install_packages_performed": install_performed,
        "runtime_server_started": runtime_started,
        "preview_server_started": False,
        "generated_code_execution_performed": runtime_started,
        "node_command_executed": node_command_executed,
        "python_command_executed": False,
        "generated_files_written": False,
        "filesystem_write_performed": False,
        "disk_write_performed": False,
        "repair_applied": False,
        "restore_executed": False,
    }


def _blocked(
    workflow_run_id: str,
    block_reason: str,
    *,
    run_plan_result: Optional[Dict[str, Any]] = None,
    approval_result: Optional[Dict[str, Any]] = None,
    workspace_root: Optional[str] = None,
    working_directory: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "success": True,
        "found": bool(run_plan_result and run_plan_result.get("found")),
        "workflow_run_id": workflow_run_id,
        "runtime_status": "blocked",
        "block_reason": block_reason,
        "safety_mode": CONTROLLED_SANDBOX_RUNTIME_SAFETY_MODE,
        "workspace_root": workspace_root,
        "working_directory": working_directory,
        "run_plan": (run_plan_result or {}).get("runtime_run_plan"),
        "runtime_approval": (approval_result or {}).get("approval_record"),
        "process": None,
        "safety_flags": _safe_flags(),
    }


def _sanitize_workspace_id(workspace_id: str) -> str:
    safe = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in workspace_id or "unknown-workspace").strip("-")
    return safe or "unknown-workspace"


def _workspace_root_for_workflow(db: Session, workflow_run_id: str) -> Optional[Path]:
    generated_file = (
        db.query(PlatformGeneratedFile)
        .filter(PlatformGeneratedFile.workflow_run_id == workflow_run_id)
        .order_by(PlatformGeneratedFile.created_at.asc())
        .first()
    )
    if not generated_file or not generated_file.workspace_id:
        return None
    return APPROVED_SANDBOX_ROOT_BASE / _sanitize_workspace_id(generated_file.workspace_id)


def _resolve_working_directory(workspace_root: Path, run_plan: Dict[str, Any]) -> Optional[Path]:
    working_directory = (run_plan.get("working_directory") or ".").strip() or "."
    candidate = (workspace_root / working_directory).resolve()
    try:
        candidate.relative_to(workspace_root.resolve())
    except ValueError:
        return None
    return candidate


def _is_approved(approval_result: Dict[str, Any]) -> bool:
    record = approval_result.get("approval_record") or {}
    return bool(approval_result.get("found") and record.get("approval_status") == "approved")


def _runtime_command(run_plan: Dict[str, Any]) -> Optional[str]:
    run_step = run_plan.get("run_step") or {}
    command = run_step.get("command") or run_plan.get("run_command")
    return command.strip() if isinstance(command, str) else None


def _install_command(run_plan: Dict[str, Any]) -> Optional[str]:
    install_step = run_plan.get("install_step") or {}
    command = install_step.get("command")
    return command.strip() if isinstance(command, str) else None


def _npm_command_args(command: str) -> Optional[List[str]]:
    if command == "npm install":
        return ["npm", "install"]
    if command == "npm run dev":
        return ["npm", "run", "dev", "--", "--host", "127.0.0.1"]
    return None


def start_controlled_sandbox_runtime_for_workflow(
    db: Session,
    workflow_run_id: str,
    *,
    perform_install: bool = False,
) -> Dict[str, Any]:
    if workflow_run_id in _RUNNING_PROCESSES and _RUNNING_PROCESSES[workflow_run_id].poll() is None:
        process = _RUNNING_PROCESSES[workflow_run_id]
        return {
            "success": True,
            "found": True,
            "workflow_run_id": workflow_run_id,
            "runtime_status": "already_running",
            "block_reason": None,
            "safety_mode": CONTROLLED_SANDBOX_RUNTIME_SAFETY_MODE,
            "process": {
                "pid": process.pid,
                "poll": process.poll(),
                "started": True,
                "already_running": True,
            },
            "safety_flags": _safe_flags(runtime_started=True, node_command_executed=True),
        }

    run_plan_result = build_runtime_run_plan_for_workflow(db, workflow_run_id=workflow_run_id)
    if not run_plan_result.get("found"):
        return _blocked(workflow_run_id, "Runtime run plan was not found.", run_plan_result=run_plan_result)

    run_plan = run_plan_result.get("runtime_run_plan") or {}
    if run_plan.get("status") != "runtime_run_plan_ready_for_approval":
        return _blocked(
            workflow_run_id,
            "Runtime run plan is not ready for approval-controlled execution.",
            run_plan_result=run_plan_result,
        )

    approval_result = get_latest_runtime_approval_for_workflow(db, workflow_run_id=workflow_run_id)
    if not _is_approved(approval_result):
        return _blocked(
            workflow_run_id,
            "Latest runtime approval record is required and must be approved.",
            run_plan_result=run_plan_result,
            approval_result=approval_result,
        )

    workspace_root = _workspace_root_for_workflow(db, workflow_run_id)
    if not workspace_root:
        return _blocked(
            workflow_run_id,
            "Workspace root could not be resolved from generated files.",
            run_plan_result=run_plan_result,
            approval_result=approval_result,
        )

    workspace_root = workspace_root.resolve()
    if not str(workspace_root).startswith(str(APPROVED_SANDBOX_ROOT_BASE.resolve())):
        return _blocked(
            workflow_run_id,
            "Workspace root is outside the approved sandbox base.",
            run_plan_result=run_plan_result,
            approval_result=approval_result,
            workspace_root=str(workspace_root),
        )

    working_directory = _resolve_working_directory(workspace_root, run_plan)
    if not working_directory:
        return _blocked(
            workflow_run_id,
            "Run plan working directory escapes the approved sandbox root.",
            run_plan_result=run_plan_result,
            approval_result=approval_result,
            workspace_root=str(workspace_root),
            working_directory=run_plan.get("working_directory"),
        )

    if not working_directory.exists():
        return _blocked(
            workflow_run_id,
            "Run plan working directory does not exist in the sandbox. Materialize approved files first.",
            run_plan_result=run_plan_result,
            approval_result=approval_result,
            workspace_root=str(workspace_root),
            working_directory=str(working_directory),
        )

    install_command = _install_command(run_plan)
    if install_command and install_command not in _ALLOWED_INSTALL_COMMANDS:
        return _blocked(
            workflow_run_id,
            "Install command is not in the V70 allowlist.",
            run_plan_result=run_plan_result,
            approval_result=approval_result,
            workspace_root=str(workspace_root),
            working_directory=str(working_directory),
        )

    run_command = _runtime_command(run_plan)
    if run_command not in _ALLOWED_RUN_COMMANDS:
        return _blocked(
            workflow_run_id,
            "Run command is not in the V70 allowlist.",
            run_plan_result=run_plan_result,
            approval_result=approval_result,
            workspace_root=str(workspace_root),
            working_directory=str(working_directory),
        )

    install_result = None
    if perform_install:
        install_args = _npm_command_args(install_command or "")
        if not install_args:
            return _blocked(
                workflow_run_id,
                "Install command could not be translated into safe argv.",
                run_plan_result=run_plan_result,
                approval_result=approval_result,
                workspace_root=str(workspace_root),
                working_directory=str(working_directory),
            )
        install_completed = subprocess.run(
            install_args,
            cwd=str(working_directory),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        install_result = {
            "command": install_command,
            "returncode": install_completed.returncode,
            "stdout_tail": install_completed.stdout[-4000:],
            "stderr_tail": install_completed.stderr[-4000:],
        }
        if install_completed.returncode != 0:
            return {
                "success": True,
                "found": True,
                "workflow_run_id": workflow_run_id,
                "runtime_status": "install_failed",
                "block_reason": "Install command failed; runtime was not started.",
                "safety_mode": CONTROLLED_SANDBOX_RUNTIME_SAFETY_MODE,
                "workspace_root": str(workspace_root),
                "working_directory": str(working_directory),
                "install_result": install_result,
                "run_plan": run_plan,
                "runtime_approval": approval_result.get("approval_record"),
                "process": None,
                "safety_flags": _safe_flags(install_performed=True, node_command_executed=True),
            }

    run_args = _npm_command_args(run_command or "")
    if not run_args:
        return _blocked(
            workflow_run_id,
            "Run command could not be translated into safe argv.",
            run_plan_result=run_plan_result,
            approval_result=approval_result,
            workspace_root=str(workspace_root),
            working_directory=str(working_directory),
        )

    env = os.environ.copy()
    env.setdefault("HOST", "127.0.0.1")
    env.setdefault("PORT", str(run_plan.get("port") or 5173))

    process = subprocess.Popen(
        run_args,
        cwd=str(working_directory),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
        env=env,
    )
    _RUNNING_PROCESSES[workflow_run_id] = process
    time.sleep(1)

    poll = process.poll()
    return {
        "success": True,
        "found": True,
        "workflow_run_id": workflow_run_id,
        "runtime_status": "running" if poll is None else "exited_early",
        "block_reason": None if poll is None else "Runtime process exited before readiness confirmation.",
        "safety_mode": CONTROLLED_SANDBOX_RUNTIME_SAFETY_MODE,
        "workspace_root": str(workspace_root),
        "working_directory": str(working_directory),
        "install_result": install_result,
        "run_plan": run_plan,
        "runtime_approval": approval_result.get("approval_record"),
        "process": {
            "pid": process.pid,
            "poll": poll,
            "started": True,
            "command": run_command,
            "argv": run_args,
            "port": run_plan.get("port") or 5173,
        },
        "safety_flags": _safe_flags(
            runtime_started=poll is None,
            install_performed=bool(install_result),
            node_command_executed=True,
        ),
    }


def get_controlled_sandbox_runtime_status(workflow_run_id: str) -> Dict[str, Any]:
    process = _RUNNING_PROCESSES.get(workflow_run_id)
    if not process:
        return {
            "success": True,
            "found": False,
            "workflow_run_id": workflow_run_id,
            "runtime_status": "not_started",
            "safety_mode": CONTROLLED_SANDBOX_RUNTIME_SAFETY_MODE,
            "process": None,
            "safety_flags": _safe_flags(),
        }

    poll = process.poll()
    return {
        "success": True,
        "found": True,
        "workflow_run_id": workflow_run_id,
        "runtime_status": "running" if poll is None else "exited",
        "safety_mode": CONTROLLED_SANDBOX_RUNTIME_SAFETY_MODE,
        "process": {
            "pid": process.pid,
            "poll": poll,
            "running": poll is None,
        },
        "safety_flags": _safe_flags(runtime_started=poll is None, node_command_executed=True),
    }


def stop_controlled_sandbox_runtime(workflow_run_id: str) -> Dict[str, Any]:
    process = _RUNNING_PROCESSES.get(workflow_run_id)
    if not process:
        return {
            "success": True,
            "found": False,
            "workflow_run_id": workflow_run_id,
            "runtime_status": "not_started",
            "safety_mode": CONTROLLED_SANDBOX_RUNTIME_SAFETY_MODE,
            "process": None,
            "safety_flags": _safe_flags(),
        }

    if process.poll() is None:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            process.wait(timeout=10)

    _RUNNING_PROCESSES.pop(workflow_run_id, None)
    return {
        "success": True,
        "found": True,
        "workflow_run_id": workflow_run_id,
        "runtime_status": "stopped",
        "safety_mode": CONTROLLED_SANDBOX_RUNTIME_SAFETY_MODE,
        "process": {
            "pid": process.pid,
            "poll": process.poll(),
            "running": False,
        },
        "safety_flags": _safe_flags(runtime_started=False, node_command_executed=True),
    }
