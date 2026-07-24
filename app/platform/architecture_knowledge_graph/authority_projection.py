from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List

from app.platform.capability_intelligence.service import discover_relevant_capabilities


ARCHITECTURE_QUERY = (
    "platform architecture runtime mission workflow repository governance provider "
    "deployment validation persistence agents infrastructure simulation sandbox"
)


def project_authorities() -> Dict[str, Any]:
    context = discover_relevant_capabilities(ARCHITECTURE_QUERY, limit=30)
    capabilities = context.get("capabilities") or context.get("records") or []
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, str]] = []
    for item in capabilities:
        record = asdict(item) if hasattr(item, "__dataclass_fields__") else dict(item)
        node_id = "service:%s" % record.get("capability_id", "unknown")
        source_paths = list(record.get("source_paths") or [])
        nodes.append(_capability_node(node_id, record, source_paths))
        for path in source_paths:
            if path.endswith(".py"):
                module_id = "module:%s" % path[:-3].replace("/", ".")
                edges.append(_edge(node_id, module_id, "owns", "capability-intelligence"))
        for dependency in record.get("dependency_evidence") or []:
            fact = _value(dependency, "fact")
            if fact:
                nodes[-1]["evidence"].append(
                    {"source": _value(dependency, "source_reference"), "kind": "dependency", "fact": fact}
                )
    return {"nodes": nodes, "edges": edges, "source": context}


def _capability_node(node_id: str, record: Dict[str, Any], paths: List[str]) -> Dict[str, Any]:
    integration = str(record.get("integration_status") or "UNKNOWN")
    production = str(record.get("production_status") or "UNKNOWN")
    lifecycle = str(record.get("lifecycle_classification") or "UNKNOWN")
    return {
        "id": node_id,
        "type": "Service",
        "name": record.get("canonical_name") or record.get("capability_id"),
        "domain": record.get("domain") or "platform",
        "purpose": record.get("purpose") or "",
        "authority": "Canonical" if integration == "INTEGRATED" else "Projection",
        "lifecycle": _lifecycle(lifecycle),
        "technology": {},
        "quality": {"validation": integration, "coverage": "Evidence-derived"},
        "ownership": {
            "module_owner": record.get("owning_layer") or "unknown",
            "repository": "tehkst/ai-app-builder-dev",
        },
        "operational": {"runtime_usage": integration, "production_usage": production},
        "evidence": [
            {"source": path, "kind": "capability-source"} for path in paths
        ],
        "unknowns": list(record.get("unknowns") or []),
        "confidence": record.get("confidence") or "UNKNOWN",
    }


def _lifecycle(value: str) -> str:
    return {
        "INTEGRATED": "Active",
        "FOUNDATION": "Dormant",
        "PLACEHOLDER": "Candidate for Removal",
    }.get(value, "Unknown")


def _value(item: Any, key: str) -> str:
    if isinstance(item, dict):
        return str(item.get(key) or "")
    return str(getattr(item, key, "") or "")


def _edge(source: str, target: str, relation: str, evidence: str) -> Dict[str, str]:
    return {"source": source, "target": target, "type": relation, "evidence": evidence}
