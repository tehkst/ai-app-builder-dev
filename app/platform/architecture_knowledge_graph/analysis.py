from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Dict, Iterable, List, Set


def enrich_graph(nodes: List[Dict[str, Any]], edges: List[Dict[str, str]]) -> None:
    inbound: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    outbound: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for edge in edges:
        outbound[edge["source"]].append(edge)
        inbound[edge["target"]].append(edge)
    for node in nodes:
        node_inbound = inbound[node["id"]]
        node_outbound = outbound[node["id"]]
        node["relationships"] = {
            "inbound": len(node_inbound),
            "outbound": len(node_outbound),
        }
        if node["type"] == "Module":
            _classify_module(node, node_inbound, node_outbound)
        node["health"] = _health(node)


def impact_report(graph: Dict[str, Any], targets: Iterable[str]) -> Dict[str, Any]:
    nodes = {node["id"]: node for node in graph["nodes"]}
    matched = _match_targets(nodes, targets)
    reverse: Dict[str, Set[str]] = defaultdict(set)
    for edge in graph["edges"]:
        reverse[edge["target"]].add(edge["source"])
    affected = _walk(reverse, matched)
    affected_nodes = [nodes[node_id] for node_id in sorted(affected) if node_id in nodes]
    modules = [node for node in affected_nodes if node["type"] == "Module"]
    tests = sorted({test for node in modules for test in node.get("quality", {}).get("tests", [])})
    deployments = [node["id"] for node in affected_nodes if node["type"] == "Deployment"]
    order = _migration_order(graph["edges"], affected)
    complexity = "high" if len(affected) > 30 else "medium" if len(affected) > 10 else "low"
    return {
        "status": "impact-computed",
        "targets": sorted(matched),
        "affected_modules": [node["id"] for node in modules],
        "affected_workflows": [node["id"] for node in affected_nodes if node["type"] in ("Workflow", "Mission")],
        "affected_tests": tests,
        "affected_deployments": deployments,
        "migration_order": order,
        "estimated_complexity": complexity,
        "blocking_dependencies": sorted(
            node["id"] for node in affected_nodes
            if node.get("health", {}).get("status") in ("Split Required", "At Risk")
        ),
        "evidence_only": True,
    }


def _classify_module(node: Dict[str, Any], inbound: List[Dict[str, str]], outbound: List[Dict[str, str]]) -> None:
    quality = node.get("quality", {})
    no_tests = not quality.get("tests")
    if not inbound and not outbound and no_tests:
        node["lifecycle"] = "Candidate for Removal"
        node["candidate_reason"] = "No import references, dependencies, or mapped tests were found."


def _health(node: Dict[str, Any]) -> Dict[str, Any]:
    quality = node.get("quality", {})
    if quality.get("line_rule") == "Split Required":
        return {"status": "Split Required", "score": 45}
    if node.get("lifecycle") == "Candidate for Removal":
        return {"status": "Review", "score": 40}
    unknowns = len(node.get("unknowns") or [])
    return {"status": "Healthy" if unknowns == 0 else "At Risk", "score": max(50, 100 - unknowns * 10)}


def _match_targets(nodes: Dict[str, Dict[str, Any]], targets: Iterable[str]) -> Set[str]:
    terms = [str(target).lower().strip() for target in targets if str(target).strip()]
    return {
        node_id for node_id, node in nodes.items()
        if any(term in ("%s %s %s" % (node_id, node.get("name", ""), node.get("path", ""))).lower() for term in terms)
    }


def _walk(reverse: Dict[str, Set[str]], roots: Set[str]) -> Set[str]:
    visited = set(roots)
    queue = deque(roots)
    while queue:
        current = queue.popleft()
        for dependent in reverse.get(current, set()):
            if dependent not in visited:
                visited.add(dependent)
                queue.append(dependent)
    return visited


def _migration_order(edges: List[Dict[str, str]], affected: Set[str]) -> List[str]:
    dependencies = defaultdict(set)
    for edge in edges:
        if edge["source"] in affected and edge["target"] in affected:
            dependencies[edge["source"]].add(edge["target"])
    return sorted(affected, key=lambda node_id: (len(dependencies[node_id]), node_id))
