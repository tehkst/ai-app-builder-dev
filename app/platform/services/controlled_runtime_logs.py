from __future__ import annotations

import subprocess
import threading
import time
from collections import deque
from typing import Any, Dict, List, Optional

from app.platform.services.controlled_runtime_registry import RUNNING_PROCESSES
from app.platform.services.controlled_runtime_safety import (
    CONTROLLED_SANDBOX_RUNTIME_LOG_SAFETY_MODE,
    log_safe_flags,
)


MAX_LOG_LINES_PER_STREAM = 200
_RUNTIME_LOGS: Dict[str, Dict[str, Any]] = {}
_RUNTIME_LOG_LOCK = threading.Lock()


def init_runtime_log_record(
    workflow_run_id: str,
    process: subprocess.Popen,
    run_command: str,
    run_args: List[str],
) -> None:
    now = time.time()
    with _RUNTIME_LOG_LOCK:
        _RUNTIME_LOGS[workflow_run_id] = {
            "workflow_run_id": workflow_run_id,
            "pid": process.pid,
            "command": run_command,
            "argv": list(run_args),
            "started_at_epoch": now,
            "last_updated_epoch": now,
            "exit_code": None,
            "stdout_lines": deque(maxlen=MAX_LOG_LINES_PER_STREAM),
            "stderr_lines": deque(maxlen=MAX_LOG_LINES_PER_STREAM),
            "stdout_line_count": 0,
            "stderr_line_count": 0,
            "readers_started": False,
            "readers_completed": False,
        }


def append_runtime_log_line(workflow_run_id: str, stream_name: str, line: str) -> None:
    normalized = line.rstrip("\n")
    with _RUNTIME_LOG_LOCK:
        record = _RUNTIME_LOGS.get(workflow_run_id)
        if not record:
            return
        key = "stdout_lines" if stream_name == "stdout" else "stderr_lines"
        count_key = "stdout_line_count" if stream_name == "stdout" else "stderr_line_count"
        record[key].append(normalized)
        record[count_key] = int(record.get(count_key) or 0) + 1
        record["last_updated_epoch"] = time.time()


def mark_runtime_log_exit(workflow_run_id: str, exit_code: Optional[int]) -> None:
    with _RUNTIME_LOG_LOCK:
        record = _RUNTIME_LOGS.get(workflow_run_id)
        if not record:
            return
        record["exit_code"] = exit_code
        record["last_updated_epoch"] = time.time()


def _mark_runtime_log_readers_started(workflow_run_id: str) -> None:
    with _RUNTIME_LOG_LOCK:
        record = _RUNTIME_LOGS.get(workflow_run_id)
        if record:
            record["readers_started"] = True
            record["last_updated_epoch"] = time.time()


def _mark_runtime_log_readers_completed(workflow_run_id: str) -> None:
    with _RUNTIME_LOG_LOCK:
        record = _RUNTIME_LOGS.get(workflow_run_id)
        if record:
            record["readers_completed"] = True
            record["last_updated_epoch"] = time.time()


def _read_stream_to_log(workflow_run_id: str, stream_name: str, stream: Any) -> None:
    try:
        for line in iter(stream.readline, ""):
            if not line:
                break
            append_runtime_log_line(workflow_run_id, stream_name, line)
    except Exception as exc:
        append_runtime_log_line(workflow_run_id, "stderr", f"[v71-log-reader-error:{stream_name}] {exc}")
    finally:
        try:
            stream.close()
        except Exception:
            pass


def _wait_for_process_exit_to_log(workflow_run_id: str, process: subprocess.Popen) -> None:
    try:
        exit_code = process.wait()
        mark_runtime_log_exit(workflow_run_id, exit_code)
    finally:
        _mark_runtime_log_readers_completed(workflow_run_id)


def start_runtime_log_readers(workflow_run_id: str, process: subprocess.Popen) -> None:
    _mark_runtime_log_readers_started(workflow_run_id)
    if process.stdout is not None:
        threading.Thread(
            target=_read_stream_to_log,
            args=(workflow_run_id, "stdout", process.stdout),
            daemon=True,
        ).start()
    if process.stderr is not None:
        threading.Thread(
            target=_read_stream_to_log,
            args=(workflow_run_id, "stderr", process.stderr),
            daemon=True,
        ).start()
    threading.Thread(
        target=_wait_for_process_exit_to_log,
        args=(workflow_run_id, process),
        daemon=True,
    ).start()


def runtime_log_snapshot(workflow_run_id: str) -> Dict[str, Any]:
    process = RUNNING_PROCESSES.get(workflow_run_id)
    with _RUNTIME_LOG_LOCK:
        record = _RUNTIME_LOGS.get(workflow_run_id)
        if not record:
            return {
                "success": True,
                "found": False,
                "workflow_run_id": workflow_run_id,
                "runtime_status": "not_started" if not process else "log_record_missing",
                "safety_mode": CONTROLLED_SANDBOX_RUNTIME_LOG_SAFETY_MODE,
                "process": None if not process else {"pid": process.pid, "poll": process.poll(), "running": process.poll() is None},
                "logs": {"stdout_tail": [], "stderr_tail": [], "stdout_line_count": 0, "stderr_line_count": 0},
                "safety_flags": log_safe_flags(),
            }
        stdout_tail = list(record.get("stdout_lines") or [])
        stderr_tail = list(record.get("stderr_lines") or [])
        exit_code = record.get("exit_code")
        poll = process.poll() if process else exit_code
        return {
            "success": True,
            "found": True,
            "workflow_run_id": workflow_run_id,
            "runtime_status": "running" if poll is None else "exited",
            "safety_mode": CONTROLLED_SANDBOX_RUNTIME_LOG_SAFETY_MODE,
            "process": {
                "pid": record.get("pid"),
                "poll": poll,
                "running": poll is None,
                "exit_code": exit_code if exit_code is not None else poll,
                "command": record.get("command"),
                "argv": record.get("argv"),
            },
            "logs": {
                "stdout_tail": stdout_tail,
                "stderr_tail": stderr_tail,
                "stdout_line_count": record.get("stdout_line_count") or 0,
                "stderr_line_count": record.get("stderr_line_count") or 0,
                "max_lines_per_stream": MAX_LOG_LINES_PER_STREAM,
                "started_at_epoch": record.get("started_at_epoch"),
                "last_updated_epoch": record.get("last_updated_epoch"),
                "readers_started": record.get("readers_started") is True,
                "readers_completed": record.get("readers_completed") is True,
            },
            "safety_flags": log_safe_flags(),
        }
