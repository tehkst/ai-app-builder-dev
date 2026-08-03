from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from app.platform.agents.builtin import register_builtin_agents
from app.platform.agents.specialists import register_specialist_agents
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.services.agent_workflow_executor_service import resume_agent_workflow
from app.platform.services.app_build_workflow_generator_service import (
    generate_app_build_workflow,
)
from app.platform.services.generated_file_persistence_service import (
    persist_generated_files_for_workflow,
)
from app.platform.services.scoping_persistence_service import (
    get_scoping_record,
    serialize_scoping_record,
)
from app.platform.services.workflow_run_persistence_service import (
    get_workflow_run_detail,
)


def resume_app_build_request(
    *,
    app_request: str,
    scoping_request_id: str,
    workflow_run_id: str,
    decision: Dict[str, Any],
    workflow_name: Optional[str] = None,
    real_bridge: bool = True,
    on_step_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """Continue a build that paused on an escalated step, after a real founder decision.

    Mirrors run_app_build_request's post-processing (link/persist/failure-fact) but
    calls resume_agent_workflow against the SAME workflow_run_id instead of starting a
    new one - see that function's docstring for why this is a real resume, not a restart.
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

        execution_result = resume_agent_workflow(
            db,
            workflow_run_id=workflow_run_id,
            steps=generated_workflow["steps"],
            decision=decision,
            workflow_name=generated_workflow["workflow_name"],
            simulation=not real_bridge,
            on_step_complete=on_step_complete,
            scoping_request_id=scoping_request_id,
        )
        workflow_detail = get_workflow_run_detail(db, workflow_run_id=workflow_run_id)
        generated_file_persistence = persist_generated_files_for_workflow(db, workflow_detail)
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
