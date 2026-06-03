from langgraph.graph import StateGraph, END

from app.ai.state import (
    ProjectState,
    MAX_FIX_ATTEMPTS,
)

from app.ai.nodes.planner import planner_node
from app.ai.nodes.architect import architect_node
from app.ai.nodes.code_generator import code_generator_node
from app.ai.nodes.reviewer import reviewer_node
from app.ai.nodes.fixer import fixer_node
from app.ai.nodes.approval import approval_node
from app.ai.nodes.file_writer import file_writer_node
from app.ai.nodes.human_review import human_review_node
from app.ai.nodes.manifest_validator import manifest_validator_node
from app.ai.nodes.manifest_generator import manifest_generator_node
from app.ai.nodes.file_generator import file_generator_node
from app.ai.nodes.interface_contract import interface_contract_node
from app.ai.nodes.template_enforcer import template_enforcer_node
from app.ai.nodes.workspace_isolation_guard import workspace_isolation_guard_node
from app.ai.nodes.dependency_guard import dependency_guard_node
from app.ai.nodes.contract_guard import contract_guard_node


workflow = StateGraph(ProjectState)

workflow.add_node("planner", planner_node)
workflow.add_node("architect", architect_node)
workflow.add_node("code_generator", code_generator_node)
workflow.add_node("reviewer", reviewer_node)
workflow.add_node("fixer", fixer_node)
workflow.add_node("approval", approval_node)
workflow.add_node("file_writer", file_writer_node)
workflow.add_node("human_review", human_review_node)
workflow.add_node("manifest_validator", manifest_validator_node)
workflow.add_node("manifest_generator", manifest_generator_node)
workflow.add_node("file_generator", file_generator_node)
workflow.add_node("interface_contract", interface_contract_node)
workflow.add_node("template_enforcer", template_enforcer_node)
workflow.add_node("workspace_isolation_guard", workspace_isolation_guard_node)
workflow.add_node("dependency_guard", dependency_guard_node)
workflow.add_node("contract_guard", contract_guard_node)

workflow.set_entry_point("planner")

workflow.add_edge("planner", "architect")
workflow.add_edge("architect", "manifest_generator")
workflow.add_edge("manifest_generator", "interface_contract")
workflow.add_edge("interface_contract", "file_generator")
workflow.add_edge("file_generator", "template_enforcer")
workflow.add_edge("template_enforcer", "workspace_isolation_guard")
workflow.add_edge("workspace_isolation_guard", "manifest_validator")
workflow.add_edge("manifest_validator", "contract_guard")
workflow.add_edge("contract_guard", "dependency_guard")
workflow.add_edge("dependency_guard", "reviewer")



def review_router(state: ProjectState):
    feedback = state.get("review_feedback", "")

    normalized_feedback = (
        feedback
        .replace("*", "")
        .replace("`", "")
        .strip()
        .lower()
    )

    if "overall status: pass" in normalized_feedback:
        return "approval"

    fix_attempts = state.get("fix_attempts", 0)

    if fix_attempts >= MAX_FIX_ATTEMPTS:
        return "human_review"

    return "fixer"


workflow.add_conditional_edges(
    "reviewer",
    review_router,
    {
        "fixer": "fixer",
        "approval": "approval",
        "human_review": "human_review",
    },
)

workflow.add_edge("fixer", "reviewer")
workflow.add_edge("approval", END)
workflow.add_edge("human_review", END)

project_graph = workflow.compile()
