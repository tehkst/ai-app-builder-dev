from __future__ import annotations

import json
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional

from app.platform.architecture_knowledge_graph.projection import build_graph
from app.platform.delivery_lineage.entries import normalize_entries
from app.platform.delivery_lineage.sources import collect_sources
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import (
    PlatformAgentTask,
    PlatformExecutionEvidence,
    PlatformOperationalEvidence,
    PlatformWorkflowRun,
)
from app.platform.services.agent_task_service import serialize_agent_task
from app.platform.services.workflow_run_persistence_service import get_workflow_run_detail


ACTIVE = {"queued", "approval_required", "approved", "running"}
TERMINAL = {"completed", "failed", "cancelled"}


def build_runtime_index(limit: int = 500) -> Dict[str, Any]:
    """Build one bounded read projection over existing durable authorities."""
    create_platform_tables()
    with PlatformSessionLocal() as db:
        task_rows = (
            db.query(PlatformAgentTask)
            .order_by(PlatformAgentTask.created_at.desc())
            .limit(limit)
            .all()
        )
        tasks = [serialize_agent_task(row) for row in task_rows]
        run_ids = list(dict.fromkeys(
            str(item.get("parent_task_id") or "") for item in tasks if item.get("parent_task_id")
        ))
        runs = {
            run_id: get_workflow_run_detail(db, workflow_run_id=run_id)
            for run_id in run_ids
        }
        execution_rows = (
            db.query(PlatformExecutionEvidence)
            .order_by(PlatformExecutionEvidence.created_at.desc())
            .limit(limit)
            .all()
        )
        operational_rows = (
            db.query(PlatformOperationalEvidence)
            .order_by(PlatformOperationalEvidence.observed_at.desc())
            .limit(limit)
            .all()
        )
    return {
        "tasks": tasks,
        "runs": runs,
        "execution_evidence": [_execution_record(row) for row in execution_rows],
        "operational_evidence": [_operational_record(row) for row in operational_rows],
    }


def project_worker_evidence(
    agent_id: str,
    runtime_index: Dict[str, Any],
    *,
    page: int = 1,
    page_size: int = 25,
) -> Dict[str, Any]:
    tasks = [
        item for item in runtime_index.get("tasks") or []
        if task_agent_id(item) == agent_id
    ]
    assignments = [_assignment(item, runtime_index.get("runs") or {}) for item in tasks]
    mission_ids = list(dict.fromkeys(
        item["mission_id"] for item in assignments if item.get("mission_id")
    ))
    lineage = _lineage_projection(agent_id, mission_ids)
    execution = _execution_projection(
        agent_id, mission_ids, runtime_index.get("execution_evidence") or []
    )
    operational = _operational_projection(
        agent_id, mission_ids, runtime_index.get("operational_evidence") or []
    )
    architecture = _architecture_projection(agent_id, lineage, execution)
    repository = _repository_projection(lineage, execution)
    deployments = _deployment_projection(lineage, execution, operational)
    history = [item for item in assignments if item.get("status") in TERMINAL]
    activity = _activity(assignments, lineage, execution, operational)
    return {
        "current_assignments": [item for item in assignments if item.get("status") in ACTIVE],
        "mission_history": _page(history, page, page_size),
        "activity": _page(activity, page, page_size),
        "lineage_contributions": _page(lineage, page, page_size),
        "architecture_contributions": _page(architecture, page, page_size),
        "repository_contributions": _page(repository, page, page_size),
        "deployment_contributions": _page(deployments, page, page_size),
        "evidence_links": {
            "lineage": "#lineage",
            "architecture": "#architecture",
            "deployments": "#deployments",
        },
    }


def project_worker_assignments(
    agent_id: str,
    runtime_index: Dict[str, Any],
) -> List[Dict[str, Any]]:
    return [
        _assignment(item, runtime_index.get("runs") or {})
        for item in runtime_index.get("tasks") or []
        if task_agent_id(item) == agent_id
    ]


def task_agent_id(task: Dict[str, Any]) -> Optional[str]:
    result = task.get("result_payload") if isinstance(task.get("result_payload"), dict) else {}
    payload = task.get("input_payload") if isinstance(task.get("input_payload"), dict) else {}
    selected = payload.get("selected_agent") if isinstance(payload.get("selected_agent"), dict) else {}
    for candidate in (
        result.get("agent_id"),
        selected.get("agent_id"),
        payload.get("assigned_agent"),
        payload.get("agent_id"),
        task.get("assigned_agent"),
    ):
        value = str(candidate or "").strip()
        if value:
            return value
    return None


def _assignment(task: Dict[str, Any], runs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    payload = task.get("input_payload") if isinstance(task.get("input_payload"), dict) else {}
    result = task.get("result_payload") if isinstance(task.get("result_payload"), dict) else {}
    run_id = str(task.get("parent_task_id") or payload.get("workflow_run_id") or "")
    run = runs.get(run_id) or {}
    state = _run_state(run)
    mission_id = str(
        payload.get("mission_id")
        or state.get("mission_id")
        or (run.get("metadata") or {}).get("mission_id")
        or ""
    ) or None
    dependencies = list(payload.get("dependencies") or payload.get("requires") or [])
    collaborators = list(payload.get("collaborating_workers") or [])
    return {
        "task_id": task.get("task_id"),
        "mission_id": mission_id,
        "mission_title": state.get("title") or state.get("founder_request"),
        "workflow_run_id": run_id or None,
        "work_package": payload.get("work_package") or payload.get("stage"),
        "assigned_role": payload.get("role") or task_agent_id(task),
        "execution_stage": payload.get("stage") or state.get("current_stage") or run.get("plan_status"),
        "title": task.get("title"),
        "status": task.get("status"),
        "priority": task.get("priority"),
        "started_at": task.get("started_at"),
        "last_activity": task.get("updated_at") or task.get("created_at"),
        "dependencies": dependencies,
        "blocker": task.get("error_message") or state.get("error"),
        "collaborating_workers": collaborators,
        "outputs": _output_references(result),
        "evidence_links": {
            "mission": "#mission-execution",
            "workflow": "#workflows",
            "lineage": "#lineage",
        },
        "source": ["PlatformAgentTask", "PlatformWorkflowRun"],
    }


def _run_state(run: Dict[str, Any]) -> Dict[str, Any]:
    for step in reversed(run.get("steps") or []):
        handler = step.get("handler_result")
        if isinstance(handler, dict) and handler.get("mission_id"):
            return handler
    return {}


def _lineage_projection(agent_id: str, mission_ids: Iterable[str]) -> List[Dict[str, Any]]:
    values = []
    for mission_id in mission_ids:
        source = collect_sources(mission_id)
        if not source.get("found"):
            continue
        for entry in normalize_entries(source):
            actor = str(entry.get("actor_id") or entry.get("actor") or "")
            if actor != agent_id:
                continue
            values.append({
                "evidence_id": entry.get("entry_id"),
                "mission_id": mission_id,
                "workflow_run_id": source.get("workflow_run_id"),
                "event": entry.get("summary"),
                "event_type": entry.get("event_type"),
                "stage": entry.get("stage"),
                "status": entry.get("status"),
                "occurred_at": entry.get("occurred_at"),
                "artifact_refs": list(entry.get("artifact_refs") or []),
                "repository_refs": list(entry.get("repository_refs") or []),
                "deployment_refs": list(entry.get("deployment_refs") or []),
                "source": entry.get("authority") or "DeliveryLineage",
                "link": "#lineage",
            })
    return values


def _execution_projection(
    agent_id: str,
    mission_ids: Iterable[str],
    records: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    missions = set(mission_ids)
    return [
        item for item in records
        if item.get("actor") == agent_id
        or (item.get("mission_id") in missions and _artifact_mentions(item.get("artifact"), agent_id))
    ]


def _operational_projection(
    agent_id: str,
    mission_ids: Iterable[str],
    records: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    missions = set(mission_ids)
    return [
        item for item in records
        if item.get("scope") in missions
        and (
            _artifact_mentions(item.get("payload"), agent_id)
            or str(item.get("authority") or "") == agent_id
        )
    ]


def _architecture_projection(
    agent_id: str,
    lineage: List[Dict[str, Any]],
    execution: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    targets = set()
    for item in lineage:
        targets.update(item.get("artifact_refs") or [])
        targets.update(item.get("repository_refs") or [])
    for item in execution:
        targets.update(_strings(item.get("artifact")))
    if not targets:
        return []
    graph = build_graph()
    values = []
    for node in graph.get("nodes") or []:
        node_text = " ".join(_strings(node))
        matched = [target for target in targets if target and target in node_text]
        if not matched:
            continue
        values.append({
            "node_id": node.get("id"),
            "name": node.get("label") or node.get("name") or node.get("id"),
            "type": node.get("type"),
            "relationship": "contributed-through-delivery-evidence",
            "evidence_refs": matched[:10],
            "agent_id": agent_id,
            "link": "#architecture",
        })
    return values


def _repository_projection(
    lineage: List[Dict[str, Any]],
    execution: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    values = []
    for item in lineage:
        for reference in item.get("repository_refs") or []:
            values.append({
                "kind": "lineage-reference",
                "reference": reference,
                "mission_id": item.get("mission_id"),
                "evidence_id": item.get("evidence_id"),
            })
    for item in execution:
        artifact = item.get("artifact") or {}
        for key in ("commit", "commit_sha", "merge_commit_sha", "pr_number", "pull_request_number", "pull_request_url"):
            if artifact.get(key) is not None:
                values.append({
                    "kind": key,
                    "reference": artifact[key],
                    "mission_id": item.get("mission_id"),
                    "evidence_id": item.get("evidence_id"),
                })
    return _unique(values, ("kind", "reference", "mission_id"))


def _deployment_projection(
    lineage: List[Dict[str, Any]],
    execution: List[Dict[str, Any]],
    operational: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    values = []
    for item in lineage:
        for reference in item.get("deployment_refs") or []:
            values.append({
                "kind": "lineage-reference",
                "reference": reference,
                "mission_id": item.get("mission_id"),
                "status": item.get("status"),
            })
    for item in execution:
        artifact = item.get("artifact") or {}
        for key in ("revision_name", "target_revision", "overall_result", "release_url", "tag_name"):
            if artifact.get(key) is not None:
                values.append({
                    "kind": key,
                    "reference": artifact[key],
                    "mission_id": item.get("mission_id"),
                    "status": item.get("outcome"),
                })
    for item in operational:
        values.append({
            "kind": item.get("evidence_type"),
            "reference": item.get("evidence_id"),
            "mission_id": item.get("scope"),
            "status": item.get("status"),
            "payload": item.get("payload"),
        })
    return _unique(values, ("kind", "reference", "mission_id"))


def _activity(
    assignments: List[Dict[str, Any]],
    lineage: List[Dict[str, Any]],
    execution: List[Dict[str, Any]],
    operational: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    values = [{
        "event": "Job %s" % str(item.get("status") or "updated").replace("_", " "),
        "mission_id": item.get("mission_id"),
        "workflow_run_id": item.get("workflow_run_id"),
        "occurred_at": item.get("last_activity"),
        "source": "PlatformAgentTask",
    } for item in assignments]
    values.extend({
        "event": item.get("event"),
        "mission_id": item.get("mission_id"),
        "workflow_run_id": item.get("workflow_run_id"),
        "occurred_at": item.get("occurred_at"),
        "source": item.get("source"),
    } for item in lineage)
    values.extend({
        "event": "%s: %s" % (item.get("capability"), item.get("outcome")),
        "mission_id": item.get("mission_id"),
        "occurred_at": item.get("created_at"),
        "source": "PlatformExecutionEvidence",
    } for item in execution)
    values.extend({
        "event": "%s: %s" % (item.get("evidence_type"), item.get("status")),
        "mission_id": item.get("scope"),
        "occurred_at": item.get("observed_at"),
        "source": "PlatformOperationalEvidence",
    } for item in operational)
    return sorted(values, key=lambda item: str(item.get("occurred_at") or ""), reverse=True)


def _execution_record(row: PlatformExecutionEvidence) -> Dict[str, Any]:
    return {
        "evidence_id": row.evidence_id,
        "mission_id": row.mission_id,
        "actor": row.actor,
        "capability": row.capability,
        "requested_action": row.requested_action,
        "outcome": row.outcome,
        "artifact": _json(row.artifact_json, {}),
        "created_at": _iso(row.created_at),
    }


def _operational_record(row: PlatformOperationalEvidence) -> Dict[str, Any]:
    return {
        "evidence_id": row.evidence_id,
        "evidence_type": row.evidence_type,
        "authority": row.authority,
        "scope": row.scope,
        "status": row.status,
        "payload": _json(row.payload_json, {}),
        "observed_at": _iso(row.observed_at),
    }


def _page(items: List[Dict[str, Any]], page: int, page_size: int) -> Dict[str, Any]:
    safe_size = max(1, min(int(page_size or 25), 100))
    safe_page = max(1, int(page or 1))
    start = (safe_page - 1) * safe_size
    return {
        "items": items[start:start + safe_size],
        "page": safe_page,
        "page_size": safe_size,
        "total": len(items),
        "has_more": start + safe_size < len(items),
    }


def _output_references(value: Any) -> List[str]:
    return [
        item for item in _strings(value)
        if "/" in item or item.startswith(("PR-", "EVIDENCE-", "REVISION-", "http"))
    ][:50]


def _strings(value: Any) -> List[str]:
    if isinstance(value, dict):
        return [item for nested in value.values() for item in _strings(nested)]
    if isinstance(value, (list, tuple, set)):
        return [item for nested in value for item in _strings(nested)]
    return [str(value)] if value is not None else []


def _artifact_mentions(value: Any, text: str) -> bool:
    return text in " ".join(_strings(value))


def _unique(items: List[Dict[str, Any]], keys: Iterable[str]) -> List[Dict[str, Any]]:
    result, seen = [], set()
    for item in items:
        marker = tuple(str(item.get(key)) for key in keys)
        if marker not in seen:
            seen.add(marker)
            result.append(item)
    return result


def _json(value: Any, default: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, ValueError):
        return default


def _iso(value: Any) -> Optional[str]:
    return value.isoformat() if value is not None and hasattr(value, "isoformat") else None
