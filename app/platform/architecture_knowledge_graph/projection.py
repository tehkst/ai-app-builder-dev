from __future__ import annotations

import hashlib
import json
import subprocess
import threading
import time
from typing import Any, Dict, List

from app.platform.architecture_knowledge_graph.adr_projection import project_architecture_decisions
from app.platform.architecture_knowledge_graph.analysis import enrich_graph
from app.platform.architecture_knowledge_graph.authority_projection import project_authorities
from app.platform.architecture_knowledge_graph.infrastructure_projection import project_infrastructure
from app.platform.architecture_knowledge_graph.operational_projection import project_operations
from app.platform.architecture_knowledge_graph.lineage_projection import project_delivery_lineage
from app.platform.architecture_knowledge_graph.repository_projection import REPO_ROOT, project_repository
from app.platform.architecture_knowledge_graph.symbol_projection import project_symbols


_LOCK = threading.RLock()
_CACHE: Dict[str, Any] = {}
_CACHE_TTL_SECONDS = 60
VIEW_TYPES = {
    "architecture": {"Module", "Service", "Artifact"},
    "runtime": {"Runtime", "Agent", "Provider", "Deployment", "Database", "Secret"},
    "mission": {"Mission", "Workflow", "Agent", "Artifact"},
    "technology": {"Technology", "Provider", "Runtime", "Module"},
    "governance": {"Service", "Artifact", "Workflow"},
    "repository": {"Repository", "Module", "Artifact"},
    # Phase 3: function/class-level nodes and "calls"/"defines" edges. Kept out of
    # every other view on purpose - "architecture" et al. stay at module granularity
    # so they aren't suddenly flooded with thousands of function nodes.
    "code": {"Module", "Function", "Class"},
    # Real, per-environment observed infrastructure (infrastructure_projection.py) -
    # separate from "runtime" so a founder can look at exactly this without the
    # in-process Agent/Provider noise "runtime" also carries.
    "infrastructure": {"Deployment", "Database", "Secret"},
}


def build_graph(refresh: bool = False) -> Dict[str, Any]:
    revision = _revision()
    with _LOCK:
        if not refresh and _fresh(revision):
            return _CACHE["graph"]
    projections = [
        project_repository(),
        project_authorities(),
        project_operations(),
        project_architecture_decisions(),
        project_delivery_lineage(),
        project_symbols(),
        project_infrastructure(),
    ]
    nodes = _unique_nodes([node for item in projections for node in item["nodes"]])
    raw_edges = [edge for item in projections for edge in item["edges"]]
    raw_edges.extend(_cross_domain_edges(nodes))
    edges = _valid_edges(nodes, raw_edges)
    enrich_graph(nodes, edges)
    graph = {
        "contract": "architecture-knowledge-graph-v1",
        "status": "ready",
        "authority": "projection-only",
        "source_revision": revision,
        "generated_at": _timestamp(),
        "cache_ttl_seconds": _CACHE_TTL_SECONDS,
        "nodes": nodes,
        "edges": edges,
        "views": sorted(VIEW_TYPES),
        "mutation_enabled": False,
    }
    graph["fingerprint"] = hashlib.sha256(
        json.dumps({"revision": revision, "nodes": nodes, "edges": edges}, sort_keys=True).encode("utf-8")
    ).hexdigest()
    with _LOCK:
        _CACHE.update({"revision": revision, "created": time.monotonic(), "graph": graph})
    return graph


def project_view(graph: Dict[str, Any], view: str) -> Dict[str, Any]:
    requested = str(view or "architecture").lower()
    types = VIEW_TYPES.get(requested, VIEW_TYPES["architecture"])
    selected = {node["id"] for node in graph["nodes"] if node["type"] in types}
    return {
        "view": requested if requested in VIEW_TYPES else "architecture",
        "nodes": [node for node in graph["nodes"] if node["id"] in selected],
        "edges": [edge for edge in graph["edges"] if edge["source"] in selected and edge["target"] in selected],
    }


def reset_projection_cache() -> None:
    with _LOCK:
        _CACHE.clear()


def _fresh(revision: str) -> bool:
    return (
        _CACHE.get("revision") == revision
        and time.monotonic() - float(_CACHE.get("created") or 0) < _CACHE_TTL_SECONDS
    )


def _unique_nodes(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    unique = {}
    for node in nodes:
        if node["id"] not in unique:
            unique[node["id"]] = node
    return [unique[key] for key in sorted(unique)]


def _valid_edges(nodes: List[Dict[str, Any]], edges: List[Dict[str, str]]) -> List[Dict[str, str]]:
    known = {node["id"] for node in nodes}
    unique = {}
    for edge in edges:
        key = (edge["source"], edge["target"], edge["type"])
        if edge["source"] in known and edge["target"] in known and edge["type"]:
            unique[key] = edge
    return [unique[key] for key in sorted(unique)]


def _cross_domain_edges(nodes: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    known = {node["id"] for node in nodes}
    edges = []
    for node in nodes:
        if node["type"] == "Module" and node.get("technology", {}).get("language") == "Python":
            edges.append({
                "source": node["id"], "target": "technology:python",
                "type": "depends_on", "evidence": "module-language-metadata",
            })
    links = [
        ("module:app.platform.server", "technology:fastapi", "depends_on", "fastapi-application"),
        ("module:app.platform.runtime.provider_router", "runtime:ai-provider-router", "implements", "provider-router"),
    ]
    for source, target, relation, evidence in links:
        if source in known and target in known:
            edges.append({"source": source, "target": target, "type": relation, "evidence": evidence})
    return edges


def _revision() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT), text=True, timeout=2
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return "repository-revision-unavailable"


def _timestamp() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
