from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class KnowledgeNode:
    node_id: str
    node_type: str
    name: str
    metadata: Dict[str, str]


@dataclass(frozen=True)
class KnowledgeEdge:
    edge_id: str
    source_node_id: str
    relationship: str
    target_node_id: str
    metadata: Dict[str, str]


NODE_TYPES = {
    "organization",
    "department",
    "team",
    "project",
    "workflow",
    "task",
    "agent",
    "memory_scope",
    "artifact",
    "requirement",
    "decision",
}


RELATIONSHIP_TYPES = {
    "contains",
    "owns",
    "executes",
    "depends_on",
    "uses_memory",
    "produces",
    "implements",
    "validates",
    "belongs_to",
}
