from langgraph.graph import StateGraph, END

from app.ai.state import ProjectState
from app.ai.nodes.file_writer import file_writer_node
from app.ai.nodes.runtime_validator import runtime_validator_node
from app.ai.nodes.runtime_error_analyzer import runtime_error_analyzer_node


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
        return "end"

    return "runtime_error_analyzer"


workflow = StateGraph(ProjectState)

workflow.add_node("approval_router", lambda state: state)
workflow.add_node("file_writer", file_writer_node)
workflow.add_node("runtime_validator", runtime_validator_node)
workflow.add_node("runtime_error_analyzer", runtime_error_analyzer_node)

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
        "end": END,
        "runtime_error_analyzer": "runtime_error_analyzer",
    },
)

workflow.add_edge("runtime_error_analyzer", END)

approval_resume_graph = workflow.compile()
