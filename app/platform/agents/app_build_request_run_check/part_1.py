# Split from the legacy single-file module to keep each file under 200 lines (this repo's
# own convention). Shared names cross the part boundary via the package __init__.py's
# namespace merge - see agent_execution_bridge_service/__init__.py for the established
# pattern this follows.
from __future__ import annotations

import argparse
import json
from typing import Any, Callable, Dict, Optional

from app.platform.agents.builtin import register_builtin_agents
from app.platform.agents.specialists import register_specialist_agents
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.services.agent_workflow_executor_service import execute_agent_workflow
from app.platform.services.app_build_workflow_generator_service import (
    generate_app_build_workflow,
)
from app.platform.services.generated_file_persistence_service import (
    persist_generated_files_for_workflow,
)
from app.platform.services.scoping_persistence_service import (
    get_scoping_record,
    link_scoping_record_to_workflow_run,
    serialize_scoping_record,
)
from app.platform.services.workflow_run_persistence_service import (
    get_workflow_run_detail,
)


def _scope_approval_required_result(
    *,
    workflow_name: Optional[str],
    app_request: str,
    reason: str,
    scoping_request: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "success": False,
        "status": "scope_approval_required",
        "reason": reason,
        "generated_workflow": False,
        "workflow_version": None,
        "workflow_name": workflow_name,
        "app_request": app_request,
        "generated_step_count": 0,
        "scoping_request": scoping_request,
        "execution": None,
        "summary": {
            "plan_status": "scope_approval_required",
            "step_count": 0,
            "completed_step_count": 0,
            "blocked_step_count": 0,
            "failed_step_count": 0,
            "workflow_run_id": None,
            "persisted": False,
            "generated_file_count": 0,
            "scope_before_build_enforced": True,
            "build_started": False,
            "materialization_performed": False,
        },
    }


def _record_build_failure_fact(app_request: str, scoping_request_id: str, workflow_detail: Dict[str, Any]) -> None:
    """Write a retro-style fact when a build doesn't fully succeed.

    Best-effort and never raises (see record_system_fact) - a memory-write
    problem must never turn a build response into an error the customer sees.
    Only called on failure/blocked outcomes, not every successful build, so this
    doesn't flood cognitive_memory with routine "build completed" noise or add
    an LLM-extraction call to the common case.
    """

    from app.platform.cognitive_memory.service import record_system_fact

    failing_steps = [
        "%s (%s)" % (step.get("title") or step.get("step_id"), step.get("status"))
        for step in workflow_detail.get("steps") or []
        if step.get("status") in {"failed", "blocked", "escalated"}
    ]
    text = (
        "Scoping-pipeline build for request %r (scoping_request_id=%s, workflow_run_id=%s) "
        "did not complete successfully - status=%s."
        % (app_request, scoping_request_id, workflow_detail.get("workflow_run_id"), workflow_detail.get("status"))
    )
    if failing_steps:
        text += " Failing/blocked steps: %s." % "; ".join(failing_steps)
    record_system_fact(text, source_type="build_failure")


def run_app_build_request(
    *,
    app_request: str,
    scoping_request_id: str,
    workflow_name: Optional[str] = None,
    real_bridge: bool = True,
    on_step_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """Run an app-build workflow against a scoping request the user has already approved.

    A scope of work (SOW) must be drafted via /product-scope/draft and approved via
    /product-scope/{id}/approve before a build can start — this is the durable,
    versioned record of what was agreed, and the basis for any later change request.
    """

    create_platform_tables()

    db = PlatformSessionLocal()
    try:
        scoping_record_model = get_scoping_record(db, scoping_request_id)
        if scoping_record_model is None:
            return _scope_approval_required_result(
                workflow_name=workflow_name,
                app_request=app_request,
                reason="scoping_request_not_found",
            )
        scoping_record = serialize_scoping_record(scoping_record_model)
        if scoping_record.get("approval_status") != "scope_approved":
            return _scope_approval_required_result(
                workflow_name=workflow_name,
                app_request=app_request,
                reason="scope_not_yet_approved",
                scoping_request=scoping_record,
            )

        normalized_request = scoping_record.get("normalized_request") or {}
        generated_workflow = generate_app_build_workflow(
            app_request=app_request,
            workflow_name=workflow_name,
            scope_of_work_markdown=scoping_record.get("scope_of_work_markdown") or "",
            acceptance_criteria=normalized_request.get("acceptance_criteria") or [],
            out_of_scope=normalized_request.get("out_of_scope") or [],
        )

        register_builtin_agents()
        register_specialist_agents()

        generated_file_persistence: Dict[str, Any] = {
            "persisted": False,
            "generated_file_count": 0,
            "write_mode": "db_preview_only",
            "disk_write_performed": False,
            "filesystem_write_performed": False,
            "generated_code_execution_performed": False,
        }
        execution_result = execute_agent_workflow(
            db,
            workflow_name=generated_workflow["workflow_name"],
            steps=generated_workflow["steps"],
            simulation=not real_bridge,
            on_step_complete=on_step_complete,
            scoping_request_id=scoping_request_id,
        )
        workflow_run_id = execution_result.get("workflow_run_id")
        if workflow_run_id:
            link_scoping_record_to_workflow_run(
                db,
                scoping_request_id=scoping_request_id,
                workflow_run_id=str(workflow_run_id),
            )
            workflow_detail = get_workflow_run_detail(db, workflow_run_id=str(workflow_run_id))
            generated_file_persistence = persist_generated_files_for_workflow(
                db,
                workflow_detail,
            )
            if execution_result.get("success") is not True:
                _record_build_failure_fact(app_request, scoping_request_id, workflow_detail)
    finally:
        db.close()

    return {
        "success": execution_result.get("success") is True,
        "status": execution_result.get("status"),
        "generated_workflow": True,
        "workflow_version": generated_workflow.get("workflow_version"),
        "workflow_name": generated_workflow.get("workflow_name"),
        "app_request": generated_workflow.get("app_request"),
        "generated_step_count": generated_workflow.get("step_count"),
        "scoping_request_id": scoping_request_id,
        "scoping_request_version": scoping_record.get("version"),
        "execution": execution_result,
        "summary": {
            "plan_status": execution_result.get("plan_status"),
            "step_count": execution_result.get("step_count"),
            "completed_step_count": execution_result.get("completed_step_count"),
            "blocked_step_count": execution_result.get("blocked_step_count"),
            "failed_step_count": execution_result.get("failed_step_count"),
            "workflow_run_id": execution_result.get("workflow_run_id"),
            "persisted": (execution_result.get("persistence") or {}).get("persisted"),
            "generated_file_count": generated_file_persistence.get("generated_file_count"),
            "generated_file_persistence": generated_file_persistence,
            "scope_before_build_enforced": True,
            "scope_approved": True,
            "build_started": True,
            "materialization_performed": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run an app-build workflow against a previously approved scoping request. "
            "Draft and approve a scope first via /product-scope/draft and "
            "/product-scope/{id}/approve (or scoping_gateway_service directly)."
        )
    )
    parser.add_argument(
        "app_request",
        help="User app request, for example: 'Build me a booking app for yoga classes'.",
    )
    parser.add_argument(
        "scoping_request_id",
        help="ID of an approved scoping request (PlatformScopingRequest.scoping_request_id).",
    )
    parser.add_argument(
        "--workflow-name",
        help="Optional workflow name override.",
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Run in safe simulation mode instead of invoking real agent handlers.",
    )
    args = parser.parse_args()

    result = run_app_build_request(
        app_request=args.app_request,
        scoping_request_id=args.scoping_request_id,
        workflow_name=args.workflow_name,
        real_bridge=not args.simulate,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
