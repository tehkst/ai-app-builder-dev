from __future__ import annotations

from app.platform.agents.builtin import register_builtin_agents
from app.platform.agents.specialists import register_specialist_agents
from app.platform.engineering.director import draft_scope_from_request
from app.platform.engineering.task_decomposer import decompose_scope_contract
from app.platform.engineering.task_step_mapper import task_graph_to_steps
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.services.agent_workflow_executor_service import execute_agent_workflow
from app.platform.services.scope_gate_service import require_scope_approval


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
        }

    create_platform_tables()
    register_builtin_agents()
    register_specialist_agents()
    db = PlatformSessionLocal()
    try:
        result = execute_agent_workflow(
            db,
            workflow_name=workflow["workflow_name"],
            steps=workflow["steps"],
            simulation=not real_bridge,
        )
    finally:
        db.close()

    return {
        "success": result.get("success") is True,
        "status": result.get("status"),
        "scope_gate": {**gate, "build_started": True},
        "task_graph": graph,
        "workflow_step_preview": workflow,
        "workflow_executed": True,
        "execution": result,
        "summary": {
            "workflow_run_id": result.get("workflow_run_id"),
            "step_count": result.get("step_count"),
            "completed_step_count": result.get("completed_step_count"),
            "blocked_step_count": result.get("blocked_step_count"),
            "failed_step_count": result.get("failed_step_count"),
            "materialization_performed": False,
        },
    }
