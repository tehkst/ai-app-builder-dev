from __future__ import annotations

import hashlib
from typing import Any, Dict, List

from app.platform.delivery_lineage.evidence_entries import authority_entries


def normalize_entries(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    entries = []
    entries.extend(_workflow_entries(source))
    entries.extend(_task_entries(source))
    entries.extend(_event_entries(source))
    entries.extend(_artifact_entries(source))
    entries.extend(authority_entries(source, _entry))
    return _ordered(_deduplicate(entries))


def _workflow_entries(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    run, state = source["run"], source["state"]
    contract = _contract(source)
    context = state.get("context") if isinstance(state.get("context"), dict) else {}
    started_at = run.get("created_at")
    values = [
        _entry(
            source, "founder_request_received", "request", "completed",
            "Founder request received for governed delivery.", "software-delivery-v1",
            "%s:founder-request" % source["mission_id"], started_at, actor="founder",
            input_hash=_hash_refs([contract.get("founder_objective") or state.get("founder_request")]),
        ),
        _entry(
            source, "intent_classified", "interpretation", "completed",
            "Conversation intent and delivery contract selected.", "conversation_intelligence",
            str(context.get("action_context_id") or "%s:intent" % source["mission_id"]), started_at,
            evidence_refs=list(contract.get("accepted_decision_references") or []),
        ),
        _entry(
            source, "mission_approved", "governance", str((contract.get("approval_state") or {}).get("mission") or "unknown"),
            "Founder-approved mission scope entered the durable runtime.", "software-delivery-v1",
            "%s:mission-approval" % source["mission_id"], started_at, actor="founder",
            approval_refs=list(contract.get("accepted_decision_references") or []),
            governance_boundary="mission-approval",
        ),
        _entry(
        source, "workflow_created", "mission", "completed",
        "Durable mission workflow created.", "PlatformWorkflowRun",
        run["workflow_run_id"], run.get("created_at"), actor="mission_runtime",
        ),
    ]
    for index, step in enumerate(state.get("steps") or []):
        values.append(_entry(
            source, "workflow_stage", str(step.get("stage") or "workflow"),
            str(step.get("status") or "unknown"), str(step.get("summary") or "Workflow stage recorded."),
            "PlatformWorkflowRun", "%s:step:%s" % (run["workflow_run_id"], index),
            step.get("at") or run.get("updated_at"), actor="mission_runtime",
            evidence_refs=[str(step.get("artifact_id"))] if step.get("artifact_id") else [],
        ))
    return values


def _task_entries(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    values = []
    for task in source["tasks"]:
        base = {"agent_task_id": task["task_id"], "actor": task.get("assigned_agent") or task.get("requested_by")}
        values.append(_entry(
            source, "agent_task_created", _task_stage(task), "created",
            "Agent task created: %s" % task["title"], "PlatformAgentTask", task["task_id"],
            task.get("created_at"), **base
        ))
        if task.get("started_at"):
            values.append(_entry(
                source, "agent_task_started", _task_stage(task), "running",
                "Agent task started.", "PlatformAgentTask", task["task_id"],
                task["started_at"], **base
            ))
        final_at = task.get("completed_at") or task.get("failed_at")
        if final_at:
            status = "completed" if task.get("completed_at") else "failed"
            values.append(_entry(
                source, "agent_task_%s" % status, _task_stage(task), status,
                task.get("error") or "Agent task %s." % status, "PlatformAgentTask",
                task["task_id"], final_at, error_code=task.get("error"),
                repair_attempt=task.get("attempts"), **base
            ))
    return values


def _event_entries(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    values = []
    for event in source["events"]:
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        values.append(_entry(
            source, str(event.get("event_type") or "event"), str(payload.get("stage") or "mission"),
            str(payload.get("status") or "recorded"), _event_summary(event),
            str(event.get("source_authority") or "PlatformOrganizationalEvent"),
            str(event.get("event_id")), event.get("occurred_at"), actor=event.get("actor"),
            caused_by=event.get("causation_id"), correlation_id=event.get("correlation_id"),
            evidence_refs=event.get("evidence_references") or [],
        ))
    return values


def _artifact_entries(source: Dict[str, Any]) -> List[Dict[str, Any]]:
    contract = _contract(source)
    values = []
    for artifact in contract.get("artifacts") or []:
        if not isinstance(artifact, dict):
            continue
        refs = list(artifact.get("evidence_references") or [])
        refs.extend(artifact.get("source_references") or [])
        values.append(_entry(
            source, "artifact_produced", str(artifact.get("artifact_type") or "artifact"),
            str(artifact.get("status") or "ready"),
            "%s produced by %s." % (str(artifact.get("artifact_type") or "Artifact").replace("_", " ").title(), artifact.get("authoring_authority") or "unknown authority"),
            str(artifact.get("authoring_authority") or "software-delivery-v1"),
            str(artifact.get("artifact_id")), artifact.get("created_at"),
            artifact_refs=[str(artifact.get("artifact_id"))], evidence_refs=refs,
            input_artifact_refs=[
                str(value) for value in artifact.get("source_references") or []
                if str(value).startswith("DELIVERY-")
            ],
            input_hash=_hash_refs(artifact.get("source_references") or []),
            output_hash=str(artifact.get("artifact_id") or "").split("-")[-1],
        ))
    return values


def _entry(source: Dict[str, Any], event_type: str, stage: str, status: str, summary: str,
           authority: str, source_id: str, occurred_at: Any, **extra: Any) -> Dict[str, Any]:
    stable = "%s:%s:%s" % (authority, source_id, event_type)
    context = source["state"].get("context") if isinstance(source["state"].get("context"), dict) else {}
    return {
        "entry_id": "LINEAGE-%s" % hashlib.sha256(stable.encode()).hexdigest()[:16].upper(),
        "mission_id": source["mission_id"], "workflow_run_id": source["workflow_run_id"],
        "occurred_at": occurred_at, "recorded_at": occurred_at, "stage": stage,
        "event_type": event_type, "status": status, "summary": summary,
        "actor_type": "agent" if extra.get("agent_task_id") else "system",
        "actor_id": extra.pop("actor", None), "authority": authority,
        "provider": context.get("provider"), "model": context.get("model"),
        "provider_configuration_source": context.get("provider_source") or "mission-context",
        "source_record_type": authority, "source_record_id": source_id,
        "artifact_refs": extra.pop("artifact_refs", []), "repository_refs": extra.pop("repository_refs", []),
        "validation_refs": extra.pop("validation_refs", []), "approval_refs": extra.pop("approval_refs", []),
        "deployment_refs": extra.pop("deployment_refs", []), "evidence_refs": extra.pop("evidence_refs", []),
        "confidence": "high", "evidence_completeness": "complete", **extra,
    }


def _ordered(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    entries.sort(key=lambda item: (item.get("occurred_at") or "", item["entry_id"]))
    for sequence, item in enumerate(entries, 1):
        item["sequence"] = sequence
    return entries


def _deduplicate(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return list({item["entry_id"]: item for item in entries}.values())


def _contract(source: Dict[str, Any]) -> Dict[str, Any]:
    value = source["state"].get("delivery_contract")
    return value if isinstance(value, dict) else {}


def _task_stage(task: Dict[str, Any]) -> str:
    return str(task.get("input", {}).get("stage") or task.get("task_type") or "agent_execution")


def _event_summary(event: Dict[str, Any]) -> str:
    return str(event.get("event_type") or "Event").replace(".", " ").replace("_", " ").title() + "."


def _hash_refs(values: List[Any]) -> str:
    return hashlib.sha256("|".join(str(value) for value in values).encode()).hexdigest() if values else ""
