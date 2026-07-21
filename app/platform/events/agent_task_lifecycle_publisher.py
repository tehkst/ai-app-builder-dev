from __future__ import annotations

from typing import Any, Mapping, Optional

from app.platform.events.event_models import AuthorityReference, build_organizational_event
from app.platform.events.event_sink import emit_organizational_event


MISSION_TASK_TYPE = "approved_mission_stage"


def publish_agent_task_lifecycle(
    task: Mapping[str, Any],
    *,
    lifecycle_status: str,
    assigned_agent: Optional[str] = None,
    result: Optional[Mapping[str, Any]] = None,
    error_message: Optional[str] = None,
) -> None:
    """Publish a non-authoritative reference after canonical task persistence succeeds."""

    if str(task.get("task_type") or "") != MISSION_TASK_TYPE:
        return

    task_id = str(task.get("task_id") or "").strip()
    workflow_run_id = str(task.get("parent_task_id") or "").strip()
    if not task_id or not workflow_run_id:
        return

    normalized_status = str(lifecycle_status or "unknown").strip().lower()
    mission_id = _mission_id(task)
    evidence_references = tuple(
        item
        for item in (
            "agent-task:%s" % task_id,
            "workflow-run:%s" % workflow_run_id,
            "mission:%s" % mission_id if mission_id else None,
        )
        if item
    )
    authority_references = (
        AuthorityReference("PlatformAgentTask", task_id, "authoritative_source"),
        AuthorityReference("PlatformWorkflowRun", workflow_run_id, "parent_workflow"),
    ) + (
        (AuthorityReference("PlatformWorkflowRun", mission_id, "mission_aggregate"),)
        if mission_id
        else ()
    )
    payload = {
        "task_id": task_id,
        "workflow_run_id": workflow_run_id,
        "mission_id": mission_id,
        "task_type": MISSION_TASK_TYPE,
        "status": normalized_status,
        "assigned_agent": assigned_agent or task.get("assigned_agent"),
        "attempts": task.get("attempts"),
        "max_attempts": task.get("max_attempts"),
        "success": None if result is None else result.get("success"),
        "error_classification": error_message,
    }
    event = build_organizational_event(
        "agent_task.%s" % normalized_status,
        source="platform.agent_worker",
        source_authority="PlatformAgentTask",
        aggregate_type="mission_workflow",
        aggregate_id=workflow_run_id,
        idempotency_key="ORG-AGENT-TASK-%s-%s" % (task_id, normalized_status),
        correlation_id=workflow_run_id,
        actor=assigned_agent or "agent_worker",
        evidence_references=evidence_references,
        authority_references=authority_references,
        payload=payload,
        metadata={"authoritative": False, "projection": "organizational_memory"},
    )
    emit_organizational_event(event)


def _mission_id(task: Mapping[str, Any]) -> Optional[str]:
    payload = task.get("input_payload")
    if isinstance(payload, Mapping):
        value = str(payload.get("mission_id") or "").strip()
        return value or None
    return None
