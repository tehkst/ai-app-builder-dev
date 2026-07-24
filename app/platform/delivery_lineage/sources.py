from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.platform.events.durable_store import DurableOrganizationalEventStore
from app.platform.operating_console.mission_run_service import load_mission_run
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import (
    PlatformAgentTask,
    PlatformExecutionEvidence,
    PlatformGovernanceApproval,
    PlatformOperationalEvidence,
    PlatformWorkflowRun,
)


def collect_sources(mission_id: str = "", workflow_run_id: str = "") -> Dict[str, Any]:
    create_platform_tables()
    run = _resolve_run(mission_id, workflow_run_id)
    if run is None:
        return {"found": False, "mission_id": mission_id or None, "workflow_run_id": workflow_run_id or None}
    state = load_mission_run(run.workflow_run_id, ensure_tables=False)
    resolved_mission = str(state.get("mission_id") or _metadata(run).get("mission_id") or "")
    with PlatformSessionLocal() as db:
        tasks = (
            db.query(PlatformAgentTask)
            .filter(PlatformAgentTask.parent_task_id == run.workflow_run_id)
            .order_by(PlatformAgentTask.created_at.asc(), PlatformAgentTask.id.asc())
            .all()
        )
        execution = (
            db.query(PlatformExecutionEvidence)
            .filter(PlatformExecutionEvidence.mission_id == resolved_mission)
            .order_by(PlatformExecutionEvidence.created_at.asc(), PlatformExecutionEvidence.id.asc())
            .all()
        )
        approvals = (
            db.query(PlatformGovernanceApproval)
            .filter(PlatformGovernanceApproval.mission_id == resolved_mission)
            .order_by(PlatformGovernanceApproval.created_at.asc(), PlatformGovernanceApproval.id.asc())
            .all()
        )
        operational = _matching_operational(db, resolved_mission, state)
    store = DurableOrganizationalEventStore(ensure_schema=lambda: None)
    events = store.list_for_correlation_id(run.workflow_run_id, limit=1000)
    events.extend(store.list_for_aggregate("mission", resolved_mission, limit=500))
    return {
        "found": True,
        "mission_id": resolved_mission,
        "workflow_run_id": run.workflow_run_id,
        "run": _run(run),
        "state": state,
        "tasks": [_task(item) for item in tasks],
        "events": _unique_events(events),
        "execution_evidence": [_execution(item) for item in execution],
        "approvals": [_approval(item) for item in approvals],
        "operational_evidence": operational,
    }


def _resolve_run(mission_id: str, workflow_run_id: str) -> Optional[PlatformWorkflowRun]:
    with PlatformSessionLocal() as db:
        query = db.query(PlatformWorkflowRun).order_by(
            PlatformWorkflowRun.created_at.desc(), PlatformWorkflowRun.id.desc()
        )
        if workflow_run_id:
            return query.filter(PlatformWorkflowRun.workflow_run_id == workflow_run_id).first()
        for row in query.limit(200).all():
            if mission_id and str(_metadata(row).get("mission_id") or "") != mission_id:
                continue
            if row.workflow_name == "Durable Board Room Mission Run":
                db.expunge(row)
                return row
    return None


def _matching_operational(db: Any, mission_id: str, state: Dict[str, Any]) -> List[Dict[str, Any]]:
    references = set(_evidence_references(state))
    rows = db.query(PlatformOperationalEvidence).order_by(
        PlatformOperationalEvidence.observed_at.asc(), PlatformOperationalEvidence.id.asc()
    ).limit(500).all()
    result = []
    for row in rows:
        payload = _json(row.payload_json, {})
        if row.evidence_id in references or mission_id in json.dumps(payload, default=str):
            result.append({
                "evidence_id": row.evidence_id, "evidence_type": row.evidence_type,
                "authority": row.authority, "scope": row.scope, "status": row.status,
                "payload": payload, "observed_at": _iso(row.observed_at),
            })
    return result


def _evidence_references(state: Dict[str, Any]) -> List[str]:
    contract = state.get("delivery_contract") if isinstance(state.get("delivery_contract"), dict) else {}
    values = list(contract.get("validation_evidence_references") or [])
    values.extend(contract.get("release_evidence_references") or [])
    values.extend([contract.get("production_verification_reference")])
    return [str(value) for value in values if value]


def _run(row: PlatformWorkflowRun) -> Dict[str, Any]:
    return {
        "workflow_run_id": row.workflow_run_id, "workflow_name": row.workflow_name,
        "status": row.status, "plan_status": row.plan_status, "metadata": _metadata(row),
        "created_at": _iso(row.created_at), "updated_at": _iso(row.updated_at),
        "completed_at": _iso(row.completed_at),
    }


def _task(row: PlatformAgentTask) -> Dict[str, Any]:
    return {
        "task_id": row.task_id, "title": row.title, "status": row.status,
        "task_type": row.task_type, "requested_by": row.requested_by,
        "assigned_agent": row.assigned_agent, "input": _json(row.input_payload_json, {}),
        "result": _json(row.result_payload_json, {}), "error": row.error_message,
        "approval_required": row.approval_required, "approval_id": row.approval_id,
        "parent_task_id": row.parent_task_id, "attempts": row.attempts,
        "max_attempts": row.max_attempts, "created_at": _iso(row.created_at),
        "started_at": _iso(row.started_at), "completed_at": _iso(row.completed_at),
        "failed_at": _iso(row.failed_at),
    }


def _execution(row: PlatformExecutionEvidence) -> Dict[str, Any]:
    return {
        "evidence_id": row.evidence_id, "actor": row.actor, "capability": row.capability,
        "requested_action": row.requested_action, "authorization": _json(row.authorization_json, {}),
        "outcome": row.outcome, "artifacts": _json(row.artifact_json, {}),
        "created_at": _iso(row.created_at),
    }


def _approval(row: PlatformGovernanceApproval) -> Dict[str, Any]:
    return {
        "approval_id": row.approval_id, "action": row.action, "scope": row.scope,
        "target": row.target, "approved_by": row.approved_by,
        "approved_at": _iso(row.approved_at), "expires_at": _iso(row.expires_at),
        "consumed_at": _iso(row.consumed_at), "revoked_at": _iso(row.revoked_at),
    }


def _unique_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return list({item["event_id"]: item for item in events}.values())


def _metadata(row: PlatformWorkflowRun) -> Dict[str, Any]:
    return _json(row.metadata_json, {})


def _json(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, ValueError):
        return fallback


def _iso(value: Any) -> Optional[str]:
    return value.isoformat() if value else None
