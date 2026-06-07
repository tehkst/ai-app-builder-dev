from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _rollback_action_for_file(file_entry: Dict[str, Any]) -> str:
    write_status = str(file_entry.get("write_status") or "").strip()

    if write_status == "preview_only":
        return "no_op_preview_only"

    if file_entry.get("previous_content_hash"):
        return "restore_previous_content"

    return "delete_created_file"


def build_generated_file_rollback_plan(
    generated_files: Optional[List[Dict[str, Any]]],
) -> Dict[str, Any]:
    safe_files = generated_files or []
    rollback_steps = []

    for index, file_entry in enumerate(safe_files, start=1):
        path = str(file_entry.get("path") or "").strip()
        content_preview = str(file_entry.get("content_preview") or "")
        action = _rollback_action_for_file(file_entry)

        rollback_steps.append(
            {
                "step": index,
                "path": path,
                "language": file_entry.get("language"),
                "write_status": file_entry.get("write_status") or "unknown",
                "rollback_action": action,
                "requires_manual_approval": action != "no_op_preview_only",
                "content_preview_hash": _sha256_text(content_preview),
                "previous_content_hash": file_entry.get("previous_content_hash"),
                "reason": (
                    "Preview-only generated file metadata does not write to disk."
                    if action == "no_op_preview_only"
                    else "File write rollback requires approval before execution."
                ),
            }
        )

    risky_steps = [
        step for step in rollback_steps
        if step["requires_manual_approval"]
    ]

    return {
        "success": True,
        "generated_file_count": len(safe_files),
        "rollback_step_count": len(rollback_steps),
        "manual_approval_required": bool(risky_steps),
        "risky_step_count": len(risky_steps),
        "rollback_mode": "plan_only",
        "rollback_steps": rollback_steps,
    }


def extract_generated_files_from_workflow_detail(
    workflow_detail: Dict[str, Any],
) -> List[Dict[str, Any]]:
    generated_files: List[Dict[str, Any]] = []

    for step in workflow_detail.get("steps") or []:
        handler_result = step.get("handler_result") or {}
        if not isinstance(handler_result, dict):
            continue

        step_files = handler_result.get("generated_files") or []
        if not isinstance(step_files, list):
            continue

        for file_entry in step_files:
            if isinstance(file_entry, dict):
                generated_files.append(
                    {
                        **file_entry,
                        "source_step_id": step.get("step_id"),
                        "source_agent_id": step.get("selected_agent_id"),
                    }
                )

    return generated_files


def build_workflow_rollback_plan(
    workflow_detail: Dict[str, Any],
) -> Dict[str, Any]:
    generated_files = extract_generated_files_from_workflow_detail(workflow_detail)
    file_plan = build_generated_file_rollback_plan(generated_files)

    return {
        "success": True,
        "workflow_run_id": workflow_detail.get("workflow_run_id"),
        "workflow_name": workflow_detail.get("workflow_name"),
        "workflow_status": workflow_detail.get("status"),
        "rollback_type": "generated_files",
        "rollback_mode": file_plan["rollback_mode"],
        "generated_file_count": file_plan["generated_file_count"],
        "rollback_step_count": file_plan["rollback_step_count"],
        "manual_approval_required": file_plan["manual_approval_required"],
        "risky_step_count": file_plan["risky_step_count"],
        "rollback_steps": file_plan["rollback_steps"],
    }
