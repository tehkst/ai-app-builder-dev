from __future__ import annotations

from typing import Dict, List, Optional


ALLOWED_RUN_COMMANDS = {"npm run dev"}
ALLOWED_INSTALL_COMMANDS = {"npm install"}


def runtime_command(run_plan: Dict[str, object]) -> Optional[str]:
    run_step = run_plan.get("run_step") or {}
    command = run_step.get("command") if isinstance(run_step, dict) else None
    command = command or run_plan.get("run_command")
    return command.strip() if isinstance(command, str) else None


def install_command(run_plan: Dict[str, object]) -> Optional[str]:
    install_step = run_plan.get("install_step") or {}
    command = install_step.get("command") if isinstance(install_step, dict) else None
    return command.strip() if isinstance(command, str) else None


def npm_command_args(command: str) -> Optional[List[str]]:
    if command == "npm install":
        return ["npm", "install"]
    if command == "npm run dev":
        return ["npm", "run", "dev", "--", "--host", "127.0.0.1"]
    return None
