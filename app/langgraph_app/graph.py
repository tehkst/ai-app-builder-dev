from langgraph.graph import StateGraph, END

from app.langgraph_app.state import AppBuilderState

from app.langgraph_app.nodes.intake_node import intake_node
from app.langgraph_app.nodes.product_spec_node import product_spec_node
from app.langgraph_app.nodes.architect_node import architect_node
from app.langgraph_app.nodes.codegen_node import codegen_node
from app.langgraph_app.nodes.qa_node import qa_node
from app.langgraph_app.nodes.security_node import security_node
from app.langgraph_app.nodes.approval_node import approval_node


def route_after_approval(state: AppBuilderState):

    if not state.get("approved"):
        return "end"

    approval_type = state.get("approval_type")

    if approval_type == "product_spec":
        return "architect"

    if approval_type == "architecture":
        return "codegen"

    if approval_type == "generated_app":
        return "end"

    return "end"


def build_app_builder_graph():

    graph = StateGraph(AppBuilderState)

    graph.add_node("intake", intake_node)
    graph.add_node("product_spec_agent", product_spec_node)
    graph.add_node("approval", approval_node)
    graph.add_node("architect", architect_node)
    graph.add_node("codegen", codegen_node)
    graph.add_node("qa", qa_node)
    graph.add_node("security", security_node)

    graph.set_entry_point("intake")

    graph.add_edge("intake", "product_spec_agent")
    graph.add_edge("product_spec_agent", "approval")

    graph.add_conditional_edges(
        "approval",
        route_after_approval,
        {
            "architect": "architect",
            "end": END,
        },
    )

    graph.add_edge("architect", "approval")
    graph.add_edge("codegen", "qa")
    graph.add_edge("qa", "security")
    graph.add_edge("security", "approval")

    return graph.compile()
