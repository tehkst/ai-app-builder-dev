from __future__ import annotations

from typing import Any, Dict, Iterable, Tuple

from app.platform.events.event_models import build_organizational_event
from app.platform.events.event_sink import emit_organizational_event


MISSION_WORKFLOW_NAME = "Durable Board Room Mission Run"
_SOURCE = "mission_runtime"
_SOURCE_AUTHORITY = "PlatformWorkflowRun"


def publish_persisted_workflow_lifecycle(result: Dict[str, Any]) -> None:
    """Publish non-authoritative lifecycle references after workflow persistence commits.

    This function must only be called after the canonical workflow transaction succeeds.
    Sink failures remain isolated by ``emit_organizational_event``.
    """

    if result.get("workflow_name") != MISSION_WORKFLOW_NAME:
        return

    workflow_run_id = str(result.get("workflow_run_id") or "").strip()
    metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
    mission_id = str(metadata.get("mission_id") or "").strip()
    if not workflow_run_id or not mission_id:
        return

    status = str(result.get("status") or "unknown")
    stage = str(result.get("plan_status") or status or "unknown")
    evidence_references = _evidence_references(result)
    common = {
        "source": _SOURCE,
        "source_authority": _SOURCE_AUTHORITY,
        "aggregate_type": "mission",
        "aggregate_id": mission_id,
        "correlation_id": workflow_run_id,
        "actor": "founder_approved_mission",
        "evidence_references": evidence_references,
        "metadata": {
            "workflow_run_id": workflow_run_id,
            "authoritative": False,
            "canonical_owner": _SOURCE_AUTHORITY,
        },
    }

    emit_organizational_event(
        build_organizational_event(
            "mission.workflow_persisted",
            idempotency_key="MISSION-WORKFLOW:%s" % workflow_run_id,
            payload={"workflow_run_id": workflow_run_id},
            **common,
        )
    )
    emit_organizational_event(
        build_organizational_event(
            "mission.stage_changed",
            idempotency_key="MISSION-STAGE:%s:%s" % (workflow_run_id, stage),
            payload={"workflow_run_id": workflow_run_id, "stage": stage, "status": status},
            **common,
        )
    )

    terminal_type = _terminal_event_type(status=status, stage=stage)
    if terminal_type:
        emit_organizational_event(
            build_organizational_event(
                terminal_type,
                idempotency_key="MISSION-TERMINAL:%s:%s" % (workflow_run_id, terminal_type),
                payload={"workflow_run_id": workflow_run_id, "stage": stage, "status": status},
                **common,
            )
        )


def _terminal_event_type(*, status: str, stage: str) -> str:
    if status == "blocked" or stage == "blocked":
        return "mission.blocked"
    if status == "failed" or stage == "failed":
        return "mission.failed"
    if status == "completed" or stage == "completed":
        return "mission.completed"
    if status == "change_set_ready" or stage == "change_set_ready":
        return "mission.change_set_verified"
    return ""


def _evidence_references(result: Dict[str, Any]) -> Tuple[str, ...]:
    references = []
    metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
    for key in ("evidence_id", "validation_record_id", "change_set_id"):
        value = metadata.get(key)
        if value:
            references.append(str(value))
    for value in _iter_reference_values(metadata.get("evidence_references")):
        references.append(value)
    return tuple(dict.fromkeys(references))


def _iter_reference_values(value: Any) -> Iterable[str]:
    if isinstance(value, (list, tuple, set)):
        for item in value:
            text = str(item).strip()
            if text:
                yield text
