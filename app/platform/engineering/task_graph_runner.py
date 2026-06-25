from __future__ import annotations

from app.platform.agents.builtin import register_builtin_agents
from app.platform.agents.specialists import register_specialist_agents
from app.platform.engineering.director import draft_scope_from_request
from app.platform.engineering.task_decomposer import decompose_scope_contract
from app.platform.engineering.task_step_mapper import task_graph_to_steps
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.services.agent_workflow_executor_service import execute_agent_workflow
from app.platform.services.generated_file_persistence_service import persist_generated_files_for_workflow
from app.platform.services.scope_gate_service import require_scope_approval
from app.platform.services.workflow_run_persistence_service import get_workflow_run_detail


def run_task_graph_request(request_text: str, approve_scope: bool = False, real_bridge: bool = False) -> dict:
    gate = require_scope_approval(request_text=request_text, scope_approved=approve_scope)
    scope = draft_scope_from_request(request_text)
    graph = decompose_scope_contract(scope)
    workflow = task_graph_to_steps(graph, request_text)

    if not gate.get("build_allowed"):
        return {
            "success": False,
            "status": "scope_approval_required",
            "scope_gate": gate,
            "task_graph": graph,
            "workflow_step_preview": workflow,
            "workflow_executed": False,
            "real_bridge": real_bridge,
            "generated_file_persistence": {"persisted": False, "generated_file_count": 0},
        }

    create_platform_tables()
    register_builtin_agents()
    register_specialist_agents()
    db = PlatformSessionLocal()
    generated_file_persistence = {"persisted": False, "generated_file_count": 0}
    try:
        result = execute_agent_workflow(
            db,
            workflow_name=workflow["workflow_name"],
            steps=workflow["steps"],
            simulation=not real_bridge,
        )
        workflow_run_id = result.get("workflow_run_id")
        if workflow_run_id:
            workflow_detail = get_workflow_run_detail(db, workflow_run_id=str(workflow_run_id))
            generated_file_persistence = persist_generated_files_for_workflow(db, workflow_detail)
    finally:
        db.close()

    return {
        "success": result.get("success") is True,
        "status": result.get("status"),
        "scope_gate": {**gate, "build_started": True},
        "task_graph": graph,
        "workflow_step_preview": workflow,
        "workflow_executed": True,
        "real_bridge": real_bridge,
        "execution": result,
        "generated_file_persistence": generated_file_persistence,
        "summary": {
            "workflow_run_id": result.get("workflow_run_id"),
            "step_count": result.get("step_count"),
            "completed_step_count": result.get("completed_step_count"),
            "blocked_step_count": result.get("blocked_step_count"),
            "failed_step_count": result.get("failed_step_count"),
            "generated_file_count": generated_file_persistence.get("generated_file_count"),
            "materialization_performed": False,
            "scope_before_build_enforced": True,
        },
    }
