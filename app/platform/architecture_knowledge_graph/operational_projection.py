from __future__ import annotations

import os
from typing import Any, Callable, Dict, List

from app.platform.agents.registry import list_agents
from app.platform.pmo.dependency_graph import story_dependency_graph
from app.platform.pipeline.mission_pipeline import build_mission_pipeline_summary
from app.platform.runtime.service import build_ai_provider_status


def project_operations() -> Dict[str, Any]:
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, str]] = []
    _project_agents(nodes)
    _project_workflows(nodes, edges)
    _project_missions(nodes, edges)
    _project_provider(nodes, edges)
    _project_technology(nodes, edges)
    _project_runtime(nodes, edges)
    return {"nodes": nodes, "edges": edges}


def _project_agents(nodes: List[Dict[str, Any]]) -> None:
    for agent in _safe(list_agents, []):
        data = dict(agent) if isinstance(agent, dict) else vars(agent)
        agent_id = str(data.get("agent_id") or data.get("name") or "unknown")
        nodes.append(_node("agent:%s" % agent_id, "Agent", data.get("name") or agent_id, "Projection"))


def _project_workflows(nodes: List[Dict[str, Any]], edges: List[Dict[str, str]]) -> None:
    graph = _safe(story_dependency_graph, {})
    for story_id, dependencies in graph.items():
        node_id = "workflow:%s" % story_id
        nodes.append(_node(node_id, "Workflow", story_id, "Projection"))
        for dependency in dependencies:
            edges.append(_edge(node_id, "workflow:%s" % dependency, "depends_on", "pmo-story-registry"))


def _project_missions(nodes: List[Dict[str, Any]], edges: List[Dict[str, str]]) -> None:
    summary = _safe(build_mission_pipeline_summary, {})
    for mission in summary.get("active_missions") or []:
        mission_id = str(mission.get("mission_id") or "").strip()
        if not mission_id:
            continue
        node_id = "mission:%s" % mission_id
        node = _node(node_id, "Mission", mission.get("title") or mission_id, "Projection")
        node["lifecycle"] = str(mission.get("status") or "Active")
        node["operational"] = {
            "runtime_usage": "Durable mission evidence",
            "production_usage": "Mission Pipeline",
        }
        node["evidence"] = [{"source": "mission-pipeline", "kind": "durable-mission"}]
        nodes.append(node)
        workflow_run_id = str(mission.get("workflow_run_id") or "").strip()
        if workflow_run_id:
            workflow_node = "workflow:%s" % workflow_run_id
            nodes.append(_node(workflow_node, "Workflow", workflow_run_id, "Canonical"))
            edges.append(_edge(node_id, workflow_node, "executes", "mission-pipeline"))
            edges.append(_edge(workflow_node, "runtime:platform", "executes", "mission-runtime"))


def _project_provider(nodes: List[Dict[str, Any]], edges: List[Dict[str, str]]) -> None:
    status = _safe(build_ai_provider_status, {})
    provider = str(status.get("provider") or os.getenv("AI_PROVIDER") or "openai")
    model = str(status.get("model") or "unknown")
    provider_id = "provider:%s" % provider
    nodes.append(_node(provider_id, "Provider", provider, "Canonical", {"model": model}))
    edges.append(_edge("runtime:ai-provider-router", provider_id, "configured_by", "runtime-provider-status"))


def _project_technology(nodes: List[Dict[str, Any]], edges: List[Dict[str, str]]) -> None:
    technologies = [
        ("technology:python", "Python", "3.9+"),
        ("technology:fastapi", "FastAPI", _package_version("fastapi")),
        ("technology:docker", "Docker", "repository-configured"),
    ]
    for node_id, name, version in technologies:
        nodes.append(_node(node_id, "Technology", name, "Projection", {"version": version}))
    edges.append(_edge("runtime:platform", "technology:python", "depends_on", "runtime"))
    edges.append(_edge("runtime:platform", "technology:fastapi", "depends_on", "server"))
    edges.append(_edge("deployment:cloud-run", "technology:docker", "configured_by", "Dockerfile"))


def _project_runtime(nodes: List[Dict[str, Any]], edges: List[Dict[str, str]]) -> None:
    nodes.extend([
        _node("runtime:platform", "Runtime", "Platform Runtime", "Canonical"),
        _node("runtime:ai-provider-router", "Runtime", "AI Provider Router", "Canonical"),
        _node("deployment:cloud-run", "Deployment", "Cloud Run Production", "Canonical"),
    ])
    edges.append(_edge("runtime:platform", "runtime:ai-provider-router", "calls", "runtime-service"))
    edges.append(_edge("deployment:cloud-run", "runtime:platform", "deploys", "cloud-run"))


def _node(node_id: str, node_type: str, name: str, authority: str, technology: Dict[str, Any] = None) -> Dict[str, Any]:
    return {
        "id": node_id, "type": node_type, "name": name, "authority": authority,
        "lifecycle": "Active", "technology": technology or {}, "quality": {},
        "ownership": {"repository": "tehkst/ai-app-builder-dev"},
        "operational": {}, "evidence": [],
    }


def _edge(source: str, target: str, relation: str, evidence: str) -> Dict[str, str]:
    return {"source": source, "target": target, "type": relation, "evidence": evidence}


def _safe(function: Callable[[], Any], fallback: Any) -> Any:
    try:
        return function()
    except Exception:
        return fallback


def _package_version(name: str) -> str:
    try:
        from importlib.metadata import version
        return version(name)
    except Exception:
        return "unknown"
