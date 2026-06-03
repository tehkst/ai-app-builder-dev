from langgraph.graph import StateGraph, END

from app.ai.state import (
    ProjectState,
    MAX_RUNTIME_FIX_ATTEMPTS,
)
from app.ai.nodes.file_writer import file_writer_node
from app.ai.nodes.runtime_validator import runtime_validator_node
from app.ai.nodes.runtime_error_analyzer import runtime_error_analyzer_node
from app.ai.nodes.runtime_fixer import runtime_fixer_node
from app.ai.nodes.workspace_registry import (
    workspace_generation_ready_node,
    workspace_generation_failed_node,
    workspace_repair_recorded_node,
)


def approval_router(state: ProjectState):
    if (
        state.get("approval_type") == "generated_app"
        and state.get("approved") is True
    ):
        return "file_writer"

    return "end"


def runtime_router(state: ProjectState):
    runtime_report = state.get("runtime_report", {})

    if runtime_report.get("passed") is True:
        return "workspace_generation_ready"

    return "runtime_error_analyzer"


def runtime_repair_router(state: ProjectState):
    runtime_fix_attempts = state.get("runtime_fix_attempts", 0)

    if runtime_fix_attempts >= MAX_RUNTIME_FIX_ATTEMPTS:
        return "workspace_generation_failed"

    return "workspace_repair_recorded"


workflow = StateGraph(ProjectState)

workflow.add_node("approval_router", lambda state: state)
workflow.add_node("file_writer", file_writer_node)
workflow.add_node("runtime_validator", runtime_validator_node)
workflow.add_node("runtime_error_analyzer", runtime_error_analyzer_node)
workflow.add_node("runtime_fixer", runtime_fixer_node)
workflow.add_node("workspace_generation_ready", workspace_generation_ready_node)
workflow.add_node("workspace_generation_failed", workspace_generation_failed_node)
workflow.add_node("workspace_repair_recorded", workspace_repair_recorded_node)

workflow.set_entry_point("approval_router")

workflow.add_conditional_edges(
    "approval_router",
    approval_router,
    {
        "file_writer": "file_writer",
        "end": END,
    },
)

workflow.add_edge("file_writer", "runtime_validator")

workflow.add_conditional_edges(
    "runtime_validator",
    runtime_router,
    {
        "workspace_generation_ready": "workspace_generation_ready",
        "runtime_error_analyzer": "runtime_error_analyzer",
    },
)

workflow.add_conditional_edges(
    "runtime_error_analyzer",
    runtime_repair_router,
    {
        "workspace_repair_recorded": "workspace_repair_recorded",
        "workspace_generation_failed": "workspace_generation_failed",
    },
)

workflow.add_edge("workspace_repair_recorded", "runtime_fixer")
workflow.add_edge("runtime_fixer", "file_writer")
workflow.add_edge("workspace_generation_ready", END)
workflow.add_edge("workspace_generation_failed", END)

approval_resume_graph = workflow.compile()
