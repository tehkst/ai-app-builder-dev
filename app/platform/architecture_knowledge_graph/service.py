from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from app.platform.architecture_knowledge_graph.analysis import impact_report
from app.platform.architecture_knowledge_graph.projection import build_graph, project_view
from app.platform.auth.service import require_founder


def build_architecture_knowledge_graph_summary() -> Dict[str, Any]:
    graph = build_graph()
    node_types = Counter(node["type"] for node in graph["nodes"])
    lifecycle = Counter(node.get("lifecycle", "Unknown") for node in graph["nodes"])
    split_required = sum(
        node.get("quality", {}).get("line_rule") == "Split Required"
        for node in graph["nodes"]
    )
    return {
        "contract": graph["contract"],
        "status": graph["status"],
        "authority": graph["authority"],
        "source_revision": graph["source_revision"],
        "fingerprint": graph["fingerprint"],
        "generated_at": graph["generated_at"],
        "node_count": len(graph["nodes"]),
        "edge_count": len(graph["edges"]),
        "node_types": dict(sorted(node_types.items())),
        "lifecycle": dict(sorted(lifecycle.items())),
        "split_required": split_required,
        "views": graph["views"],
        "cache_ttl_seconds": graph["cache_ttl_seconds"],
        "mutation_enabled": False,
    }


def build_architecture_knowledge_graph(payload: Dict[str, Any]) -> Dict[str, Any]:
    denied = _authorize(payload)
    if denied:
        return denied
    graph = build_graph(bool(payload.get("refresh")))
    view = project_view(graph, str(payload.get("view") or "architecture"))
    return {
        "contract": graph["contract"],
        "status": "projection-ready",
        "source_revision": graph["source_revision"],
        "fingerprint": graph["fingerprint"],
        "generated_at": graph["generated_at"],
        "view": view["view"],
        "nodes": view["nodes"],
        "edges": view["edges"],
        "mutation_enabled": False,
    }


def inspect_architecture_impact(payload: Dict[str, Any]) -> Dict[str, Any]:
    denied = _authorize(payload)
    if denied:
        return denied
    raw_targets = payload.get("targets") or [payload.get("target") or payload.get("query") or ""]
    targets: List[str] = [str(value) for value in raw_targets if str(value).strip()]
    if not targets:
        return {"status": "invalid-request", "error": "At least one impact target is required."}
    report = impact_report(build_graph(bool(payload.get("refresh"))), targets)
    report.update({"contract": "architecture-impact-v1", "mutation_enabled": False})
    return report


def _authorize(payload: Dict[str, Any]) -> Dict[str, Any]:
    founder = require_founder(payload)
    if founder.get("authorized"):
        return {}
    return {
        "status": "unauthorized",
        "authenticated": False,
        "error": "Founder authentication is required for architecture evidence.",
    }
