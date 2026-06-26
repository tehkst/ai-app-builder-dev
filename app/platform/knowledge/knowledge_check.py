from __future__ import annotations

from app.platform.knowledge.models import NODE_TYPES, RELATIONSHIP_TYPES
from app.platform.knowledge.registry import build_knowledge_edges, build_knowledge_nodes


REQUIRED_NODES = {
    "ai_software_factory",
    "architecture",
    "backend",
    "database",
    "frontend",
    "quality",
    "transport_lead_crm",
    "architect_agent",
    "backend_builder_agent",
    "database_builder_agent",
    "frontend_builder_agent",
    "reviewer_agent",
    "test_agent",
}


def main() -> None:
    nodes = build_knowledge_nodes()
    edges = build_knowledge_edges()

    assert REQUIRED_NODES.issubset(set(nodes)), sorted(set(REQUIRED_NODES).difference(nodes))
    assert edges, "knowledge graph edges are required"

    for node in nodes.values():
        assert node.node_id, node
        assert node.node_type in NODE_TYPES, node
        assert node.name, node

    for edge in edges:
        assert edge.edge_id, edge
        assert edge.relationship in RELATIONSHIP_TYPES, edge
        assert edge.source_node_id in nodes, edge
        if not edge.target_node_id.startswith("artifact:"):
            assert edge.target_node_id in nodes, edge

    organization_edges = [edge for edge in edges if edge.source_node_id == "ai_software_factory"]
    assert organization_edges, edges

    project_edges = [edge for edge in edges if edge.source_node_id == "transport_lead_crm"]
    assert project_edges, edges

    print("ENGINEERING KNOWLEDGE GRAPH CHECK PASSED")


if __name__ == "__main__":
    main()
