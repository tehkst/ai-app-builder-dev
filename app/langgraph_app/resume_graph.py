from langgraph.graph import StateGraph, END

from app.langgraph_app.state import AppBuilderState
from app.langgraph_app.nodes.architect_node import architect_node
from app.langgraph_app.nodes.codegen_node import codegen_node
from app.langgraph_app.nodes.qa_node import qa_node
from app.langgraph_app.nodes.security_node import security_node
from app.langgraph_app.nodes.approval_node import approval_node


def route_resume(state: AppBuilderState):
    approval_type = state.get("approval_type")

    if approval_type == "product_spec" and state.get("approved") is True:
        return "architect"

    if approval_type == "architecture" and state.get("approved") is True:
        return "codegen"

    return "end"


def build_resume_graph():
    graph = StateGraph(AppBuilderState)

    graph.add_node("approval_router", lambda state: state)
    graph.add_node("architect", architect_node)
    graph.add_node("codegen", codegen_node)
    graph.add_node("qa", qa_node)
    graph.add_node("security", security_node)
    graph.add_node("approval", approval_node)

    graph.set_entry_point("approval_router")

    graph.add_conditional_edges(
        "approval_router",
        route_resume,
        {
            "architect": "architect",
            "codegen": "codegen",
            "end": END,
        },
    )

    graph.add_edge("architect", "approval")
    graph.add_edge("codegen", "qa")
    graph.add_edge("qa", "security")
    graph.add_edge("security", "approval")

    return graph.compile()
