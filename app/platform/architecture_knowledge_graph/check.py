from __future__ import annotations

from unittest.mock import patch

from app.platform.architecture_knowledge_graph.analysis import impact_report
from app.platform.architecture_knowledge_graph.projection import build_graph, project_view, reset_projection_cache
from app.platform.architecture_knowledge_graph.service import build_architecture_knowledge_graph
from app.platform.coding_agent.dependency_analyzer import _resolve_import


def main() -> None:
    reset_projection_cache()
    graph = build_graph(refresh=True)
    node_ids = [node["id"] for node in graph["nodes"]]
    edge_keys = [(edge["source"], edge["target"], edge["type"]) for edge in graph["edges"]]
    assert graph["authority"] == "projection-only"
    assert graph["mutation_enabled"] is False
    assert len(node_ids) == len(set(node_ids)), "duplicate graph nodes"
    assert len(edge_keys) == len(set(edge_keys)), "duplicate graph edges"
    assert all(edge["type"] for edge in graph["edges"]), "anonymous edge"
    assert all(edge["source"] in node_ids and edge["target"] in node_ids for edge in graph["edges"])
    connected = {edge["source"] for edge in graph["edges"]} | {edge["target"] for edge in graph["edges"]}
    assert all(
        node["id"] in connected or node.get("lifecycle") == "Candidate for Removal"
        for node in graph["nodes"]
        if node["type"] == "Module"
    ), "unclassified orphan module"
    assert all("health" in node for node in graph["nodes"])
    assert all("line_rule" in node["quality"] for node in graph["nodes"] if node["type"] == "Module")
    assert _resolve_import(
        "app.platform.runtime.service.build_ai_provider_status",
        {"app.platform.runtime.service": "app/platform/runtime/service.py"},
    ) == "app.platform.runtime.service"
    assert project_view(graph, "technology")["nodes"]
    assert project_view(graph, "governance")["nodes"]
    report = impact_report(graph, ["Python"])
    assert report["targets"]
    assert len(report["affected_modules"]) > 100
    assert report["estimated_complexity"] in ("low", "medium", "high")
    with patch("app.platform.architecture_knowledge_graph.service.require_founder", return_value={"authorized": False}):
        assert build_architecture_knowledge_graph({"token": "invalid"})["status"] == "unauthorized"
    candidates = [node for node in graph["nodes"] if node.get("lifecycle") == "Candidate for Removal"]
    assert all("candidate_reason" in node or node["type"] == "Service" for node in candidates)
    print("ARCHITECTURE KNOWLEDGE GRAPH CHECK PASSED")


if __name__ == "__main__":
    main()
