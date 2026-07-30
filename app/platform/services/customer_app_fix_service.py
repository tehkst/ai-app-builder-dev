from __future__ import annotations

from typing import Any, Dict

from sqlalchemy.orm import Session

from app.platform.services.app_generation_service import fix_app_build_files
from app.platform.services.generated_file_persistence_service import (
    list_persisted_generated_files,
    persist_generated_files_for_workflow,
)
from app.platform.services.scoping_persistence_service import (
    get_scoping_record,
    serialize_scoping_record,
)


def apply_customer_reported_fix(
    db: Session,
    *,
    scoping_request_id: str,
    bug_report: str,
) -> Dict[str, Any]:
    """Fix a customer-reported bug in an already-built project's generated files.

    Loads the project's current generated files, asks fix_app_build_files for a
    corrected file set (with a required regression test), and - on success -
    persists the result as the new authoritative generated files for this
    project's workflow run, superseding the previous versions by path (the same
    upsert semantics every other generated-file write path already relies on).
    """

    record_model = get_scoping_record(db, scoping_request_id)
    if record_model is None:
        return {"success": False, "status": "not_found", "blocked_reason": "Project not found."}

    record = serialize_scoping_record(record_model)
    workflow_run_id = record.get("workflow_run_id")
    if not workflow_run_id:
        return {
            "success": False,
            "status": "no_build_yet",
            "blocked_reason": "This project has not been built yet - there is nothing to fix.",
        }

    existing = list_persisted_generated_files(db, workflow_run_id)
    previous_files = [
        {
            "path": item.get("path"),
            "language": item.get("language"),
            "content": item.get("content_preview"),
        }
        for item in existing.get("generated_files") or []
    ]
    if not previous_files:
        return {
            "success": False,
            "status": "no_files_to_fix",
            "blocked_reason": "No generated files were found for this project's build.",
        }

    normalized_request = record.get("normalized_request") or {}
    fix_result = fix_app_build_files(
        app_request=str(normalized_request.get("app_idea") or ""),
        scope_of_work_markdown=record.get("scope_of_work_markdown") or "",
        acceptance_criteria=normalized_request.get("acceptance_criteria") or [],
        out_of_scope=normalized_request.get("out_of_scope") or [],
        previous_files=previous_files,
        bug_report=bug_report,
    )

    if not fix_result.get("success"):
        _record_fix_failure_fact(scoping_request_id, bug_report, fix_result)
        return {
            "success": False,
            "status": "fix_blocked",
            "blocked_reason": fix_result.get("blocked_reason"),
            "failed_checks": fix_result.get("failed_checks") or [],
        }

    fixed_files = fix_result.get("files") or []
    workflow_detail = {
        "workflow_run_id": workflow_run_id,
        "steps": [
            {
                "step_id": "bug_fix",
                "selected_agent_id": "bug_fix_agent",
                "handler_result": {"generated_files": fixed_files},
            }
        ],
    }
    persistence = persist_generated_files_for_workflow(db, workflow_detail)

    return {
        "success": True,
        "status": "fixed",
        "scoping_request_id": scoping_request_id,
        "workflow_run_id": workflow_run_id,
        "app_name": fix_result.get("app_name"),
        "summary": fix_result.get("summary"),
        "regression_test_paths": fix_result.get("regression_test_paths") or [],
        "fixed_file_count": len(fixed_files),
        "generation": fix_result.get("generation") or {},
        "persistence": persistence,
    }


def _record_fix_failure_fact(scoping_request_id: str, bug_report: str, fix_result: Dict[str, Any]) -> None:
    """Best-effort retro fact when a customer-reported fix doesn't complete.

    Mirrors _record_build_failure_fact in app_build_request_run_check.py - never
    raises, and only fires on the failure path so cognitive_memory isn't flooded
    with routine successful fixes.
    """

    from app.platform.cognitive_memory.service import record_system_fact

    text = (
        "Customer-reported bug fix for scoping_request_id=%s did not complete - %s. Bug report: %r."
        % (scoping_request_id, fix_result.get("blocked_reason"), bug_report)
    )
    record_system_fact(text, source_type="bug_fix_failure")
