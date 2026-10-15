"""Nautilus repair proposals: turn an approved-flow repair plan into concrete file changes.

Nautilus works on a scratch copy of the sandbox. It may read files, run read-only inspection
commands and edit the copy, but never runs generated code (the repair flow's existing rule:
no generated-code execution before approval). The result is stored as a proposal; applying
it goes through the existing approval gate and repair executor (see apply.py).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.platform.nautilus.loop import AgentLoop, AgentLoopConfig
from app.platform.nautilus.messages import ChatFn
from app.platform.nautilus.permissions import PermissionPolicy
from app.platform.nautilus.tools import ToolRegistry
from app.platform.nautilus.workspace_tools import build_workspace_tools
from app.platform.services.nautilus_repair_service.sandbox import resolve_workflow_sandbox
from app.platform.services.nautilus_repair_service.workspace_copy import (
    detect_changes, diverged_paths, make_scratch_copy, remove_scratch_copy, snapshot_files,
)
from app.platform.services.repair_plan_generator_service import generate_repair_plan_for_workflow

NAUTILUS_REPAIR_SAFETY_MODE = "nautilus_repair_proposal_scratch_copy_no_execution"
DEFAULT_MAX_TURNS = 20
_PROPOSALS: Dict[str, List[Dict[str, Any]]] = {}

SYSTEM_PROMPT = (
    "You are the AI Software Factory repair engineer. You are working in a scratch copy of a "
    "generated application. Diagnose the runtime failure from the evidence, inspect the relevant "
    "files, and fix it by editing files with write_file. You cannot run the application, its tests "
    "or any interpreter; only read-only inspection commands (ls, cat, grep, find, ...) are allowed. "
    "Make the smallest change that fixes the failure. Do not touch unrelated files. Finish with a "
    "short explanation of the root cause and what you changed."
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _proposal_permissions() -> PermissionPolicy:
    # write_file only ever lands in the scratch copy; run_command is limited to the smart-mode
    # read-only allowlist because the approver refuses every other command.
    return PermissionPolicy("smart", approver=lambda call: call.name == "write_file")


def build_repair_goal(repair_plan: Dict[str, Any]) -> str:
    candidates = repair_plan.get("target_file_candidates") or []
    lines = [
        f"Failure category: {repair_plan.get('failure_category')}",
        f"Repair kind: {repair_plan.get('repair_kind')}",
        f"Suggested approach: {repair_plan.get('proposed_change_summary')}",
        "Runtime evidence:",
        *[f"  {line}" for line in repair_plan.get("rationale") or []],
    ]
    if candidates:
        lines.append("Files the approved repair plan allows you to change (other edits will be rejected "
                     "at apply time): " + ", ".join(candidates))
    lines.append("Fix this failure.")
    return "\n".join(lines)


def _blocked(workflow_run_id: str, reason: str, repair_plan: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"success": True, "workflow_run_id": workflow_run_id, "safety_mode": NAUTILUS_REPAIR_SAFETY_MODE,
            "proposal_status": "blocked", "block_reason": reason, "repair_plan": repair_plan,
            "proposal": None, "generated_code_execution_performed": False, "sandbox_modified": False}


def propose_nautilus_repair(*, db: Any, workflow_run_id: str, chat: Optional[ChatFn] = None,
                            requested_by: str = "platform_admin", max_turns: int = DEFAULT_MAX_TURNS) -> Dict[str, Any]:
    plan_result = generate_repair_plan_for_workflow(workflow_run_id)
    repair_plan = plan_result.get("repair_plan") or {}
    if not repair_plan.get("plan_needed"):
        return _blocked(workflow_run_id, "No repair plan is needed for this workflow run.", repair_plan)
    sandbox, reason = resolve_workflow_sandbox(db, workflow_run_id)
    if sandbox is None:
        return _blocked(workflow_run_id, reason or "Workflow sandbox could not be resolved.", repair_plan)
    if chat is None:
        from app.platform.nautilus.chat_providers import build_chat_fn

        chat = build_chat_fn()

    copy_root = make_scratch_copy(sandbox)
    try:
        baseline = snapshot_files(copy_root)
        loop = AgentLoop(chat=chat, tools=ToolRegistry(build_workspace_tools(str(copy_root))),
                         system_prompt=SYSTEM_PROMPT, permissions=_proposal_permissions(),
                         workspace_root=str(copy_root), config=AgentLoopConfig(max_turns=max_turns))
        run = loop.run(build_repair_goal(repair_plan))
        changes = detect_changes(baseline, copy_root)
    finally:
        remove_scratch_copy(copy_root)

    candidates = set(repair_plan.get("target_file_candidates") or [])
    for change in changes["changed"]:
        change["within_plan_candidates"] = not candidates or change["path"] in candidates
    diverged = diverged_paths(baseline, sandbox, [change["path"] for change in changes["changed"]])
    status = "proposed" if changes["changed"] else "no_changes_proposed"
    if run.status != "completed":
        status = "agent_incomplete" if changes["changed"] else "agent_failed"
    elif diverged:
        status = "sandbox_changed_during_generation"
    proposal = {
        "proposal_id": "NAUTILUS-REPAIR-" + uuid.uuid4().hex[:12].upper(),
        "workflow_run_id": workflow_run_id, "sandbox_root": str(sandbox), "created_at": _now_iso(),
        "requested_by": requested_by, "proposal_status": status, "agent_status": run.status,
        "agent_error": run.error, "explanation": run.final_text, "turns": run.turns,
        "tool_calls": [{"name": r.name, "outcome": r.outcome} for r in run.tool_calls],
        "changes": changes["changed"], "unsupported_changes": changes["unsupported"],
        "diverged_paths": diverged, "failure_category": repair_plan.get("failure_category"),
    }
    _PROPOSALS.setdefault(workflow_run_id, []).append(proposal)
    return {"success": True, "workflow_run_id": workflow_run_id, "safety_mode": NAUTILUS_REPAIR_SAFETY_MODE,
            "proposal_status": status, "block_reason": None, "repair_plan": repair_plan, "proposal": proposal,
            "generated_code_execution_performed": False, "sandbox_modified": False}


def latest_nautilus_proposal(workflow_run_id: str) -> Optional[Dict[str, Any]]:
    history = _PROPOSALS.get(workflow_run_id) or []
    return history[-1] if history else None


def get_nautilus_repair_proposals(workflow_run_id: str) -> Dict[str, Any]:
    return {"success": True, "workflow_run_id": workflow_run_id, "safety_mode": NAUTILUS_REPAIR_SAFETY_MODE,
            "history": _PROPOSALS.get(workflow_run_id, [])}


def reset_nautilus_repair_proposals_for_check() -> None:
    _PROPOSALS.clear()
