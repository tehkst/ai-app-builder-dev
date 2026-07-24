"""Read-only Architecture Knowledge Graph projection."""

from app.platform.architecture_knowledge_graph.service import (
    build_architecture_knowledge_graph,
    build_architecture_knowledge_graph_summary,
    inspect_architecture_impact,
)

__all__ = [
    "build_architecture_knowledge_graph",
    "build_architecture_knowledge_graph_summary",
    "inspect_architecture_impact",
]
