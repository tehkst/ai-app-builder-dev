"""Built-in tools that let an agent work inside one generated-app workspace.

Every path goes through the existing filesystem write guard, so the agent can never read
or write outside its workspace (FACTORY_CODE_IMMUTABILITY_RULE). Commands run without a
shell, inside the workspace, with secret-looking environment variables removed.
"""
from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from app.platform.agent_loop.tools import Tool, object_schema
from app.platform.guards.filesystem_write_guard import validate_generated_file_write_path

DEFAULT_COMMAND_TIMEOUT_SECONDS = 120
MAX_LISTED_FILES = 500
SECRET_ENV_MARKERS = ("KEY", "SECRET", "TOKEN", "PASSWORD", "CREDENTIAL", "DATABASE_URL")
SKIPPED_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}


class WorkspaceToolError(RuntimeError):
    pass


def _resolve(workspace_root: str, relative_path: str) -> Path:
    verdict = validate_generated_file_write_path(workspace_root, relative_path)
    if not verdict["allowed"]:
        raise WorkspaceToolError(f"Path '{relative_path}' rejected: {verdict['reason']}")
    return Path(verdict["resolved_target_path"])


def scrubbed_environment() -> Dict[str, str]:
    return {
        name: value
        for name, value in os.environ.items()
        if not any(marker in name.upper() for marker in SECRET_ENV_MARKERS)
    }


def run_workspace_command(workspace_root: str, command: str, timeout: int = DEFAULT_COMMAND_TIMEOUT_SECONDS) -> Dict[str, Any]:
    argv = shlex.split(command)
    if not argv:
        raise WorkspaceToolError("Command is empty.")
    try:
        completed = subprocess.run(
            argv,
            cwd=str(Path(workspace_root).resolve()),
            env=scrubbed_environment(),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return {"exit_code": 127, "output": f"Command not found: {argv[0]}"}
    except subprocess.TimeoutExpired:
        return {"exit_code": 124, "output": f"Command timed out after {timeout} seconds."}
    output = (completed.stdout or "") + (("\n" + completed.stderr) if completed.stderr else "")
    return {"exit_code": completed.returncode, "output": output.strip()}


def build_workspace_tools(workspace_root: str, command_timeout: int = DEFAULT_COMMAND_TIMEOUT_SECONDS) -> List[Tool]:
    root = Path(workspace_root).resolve()

    def read_file(args: Dict[str, Any]) -> str:
        target = _resolve(workspace_root, str(args["path"]))
        if not target.is_file():
            raise WorkspaceToolError(f"File not found: {args['path']}")
        return target.read_text(encoding="utf-8", errors="replace")

    def list_files(args: Dict[str, Any]) -> str:
        sub = str(args.get("path") or ".").strip()
        base = root if sub in ("", ".", "./") else _resolve(workspace_root, sub)
        if not base.is_dir():
            raise WorkspaceToolError(f"Directory not found: {sub}")
        found: List[str] = []
        for current, dirs, files in os.walk(base):
            dirs[:] = sorted(d for d in dirs if d not in SKIPPED_DIRS)
            for name in sorted(files):
                found.append(Path(current, name).relative_to(root).as_posix())
                if len(found) >= MAX_LISTED_FILES:
                    return "\n".join(found) + f"\n... (stopped at {MAX_LISTED_FILES} files)"
        return "\n".join(found) or "(no files)"

    def write_file(args: Dict[str, Any]) -> str:
        target = _resolve(workspace_root, str(args["path"]))
        target.parent.mkdir(parents=True, exist_ok=True)
        content = str(args["content"])
        target.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} characters to {target.relative_to(root).as_posix()}."

    def run_command(args: Dict[str, Any]) -> str:
        result = run_workspace_command(workspace_root, str(args["command"]), command_timeout)
        return f"exit_code: {result['exit_code']}\n{result['output']}"

    path_prop = {"type": "string", "description": "Path relative to the workspace root."}
    return [
        Tool("read_file", "Read a UTF-8 text file from the workspace.",
             object_schema({"path": path_prop}, ["path"]), read_file, read_only=True),
        Tool("list_files", "List files in the workspace (or a sub-directory), recursively.",
             object_schema({"path": path_prop}), list_files, read_only=True),
        Tool("write_file", "Create or overwrite a text file in the workspace.",
             object_schema({"path": path_prop, "content": {"type": "string"}}, ["path", "content"]),
             write_file),
        Tool("run_command",
             "Run a command in the workspace (no shell: pipes, redirects and && are not supported). "
             "Returns the exit code and combined output.",
             object_schema({"command": {"type": "string"}}, ["command"]), run_command),
    ]
