from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Mapping, Tuple


@dataclass(frozen=True)
class KnowledgeNode:
    """A non-authoritative pointer to one canonical platform entity."""

    authority: str
    entity_id: str

    @property
    def key(self) -> str:
        return f"{self.authority}:{self.entity_id}"

    def as_dict(self) -> Mapping[str, str]:
        return {"authority": self.authority, "entity_id": self.entity_id}


@dataclass(frozen=True)
class KnowledgeEdge:
    """A relationship observed in an organizational event."""

    source_key: str
    target_key: str
    relationship: str
    event_id: str

    def as_dict(self) -> Mapping[str, str]:
        return {
            "source_key": self.source_key,
            "target_key": self.target_key,
            "relationship": self.relationship,
            "event_id": self.event_id,
        }


@dataclass(frozen=True)
class GovernedKnowledgeProjection:
    """Replayable read projection derived only from governed organizational events."""

    nodes: Tuple[KnowledgeNode, ...] = field(default_factory=tuple)
    edges: Tuple[KnowledgeEdge, ...] = field(default_factory=tuple)
    event_ids: Tuple[str, ...] = field(default_factory=tuple)
    authoritative: bool = False

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "nodes": [node.as_dict() for node in self.nodes],
            "edges": [edge.as_dict() for edge in self.edges],
            "event_ids": list(self.event_ids),
            "authoritative": self.authoritative,
        }


def build_governed_knowledge_projection(
    events: Iterable[Mapping[str, Any]],
) -> GovernedKnowledgeProjection:
    """Build a deterministic authority graph without copying canonical entity state."""

    nodes: Dict[str, KnowledgeNode] = {}
    edges: Dict[Tuple[str, str, str, str], KnowledgeEdge] = {}
    event_ids = []

    for event in events:
        event_id = str(event.get("event_id") or "").strip()
        if not event_id:
            continue
        event_ids.append(event_id)
        references = _normalized_references(event.get("authority_references"))
        if not references:
            continue

        for reference in references:
            node = KnowledgeNode(reference["authority"], reference["entity_id"])
            nodes[node.key] = node

        roots = [reference for reference in references if reference["relationship"] == "authoritative_source"]
        if not roots:
            roots = references[:1]

        for root in roots:
            source = KnowledgeNode(root["authority"], root["entity_id"])
            for reference in references:
                target = KnowledgeNode(reference["authority"], reference["entity_id"])
                if source.key == target.key:
                    continue
                edge = KnowledgeEdge(
                    source_key=source.key,
                    target_key=target.key,
                    relationship=reference["relationship"],
                    event_id=event_id,
                )
                edges[(edge.source_key, edge.target_key, edge.relationship, edge.event_id)] = edge

    return GovernedKnowledgeProjection(
        nodes=tuple(nodes[key] for key in sorted(nodes)),
        edges=tuple(edges[key] for key in sorted(edges)),
        event_ids=tuple(dict.fromkeys(event_ids)),
    )


def _normalized_references(value: Any) -> Tuple[Dict[str, str], ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    normalized = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        authority = str(item.get("authority") or "").strip()
        entity_id = str(item.get("entity_id") or "").strip()
        relationship = str(item.get("relationship") or "authoritative_source").strip()
        if authority and entity_id and relationship:
            normalized.append(
                {
                    "authority": authority,
                    "entity_id": entity_id,
                    "relationship": relationship,
                }
            )
    return tuple(normalized)
