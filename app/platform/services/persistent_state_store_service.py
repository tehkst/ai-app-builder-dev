from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import (
    PlatformModuleRolloutDecision,
    PlatformModuleRolloutEvent,
    PlatformSelfBuildModuleRequest,
    PlatformSelfBuildModuleRequestEvent,
    utc_now,
)

V82_PERSISTENT_STATE_SAFETY_MODE = "persistent_state_store_v82_db_backed_gate_preserving"


def _loads_json(value: Optional[str], default: Any) -> Any:
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _dumps_json(value: Any) -> str:
    return json.dumps(value if value is not None else {}, sort_keys=True)


def _session_scope():
    create_platform_tables()
    return PlatformSessionLocal()


def _request_to_dict(record: PlatformSelfBuildModuleRequest) -> Dict[str, Any]:
    return {
        "request_id": record.request_id,
        "status": record.status,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        "requested_by": record.requested_by,
        "module_name": record.module_name,
        "module_goal": record.module_goal,
        "acceptance_criteria": _loads_json(record.acceptance_criteria_json, []),
        "notes": record.notes,
        "workflow_run_id": record.workflow_run_id,
        "handoff_status": record.handoff_status,
        "linked_by": record.linked_by,
    }


def _request_event_to_dict(record: PlatformSelfBuildModuleRequestEvent) -> Dict[str, Any]:
    return {
        "request_id": record.request_id,
        "action": record.action,
        "status": record.status,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "workflow_run_id": record.workflow_run_id,
        "module_name": record.module_name,
        "details": _loads_json(record.details_json, {}),
    }


def _rollout_decision_to_dict(record: PlatformModuleRolloutDecision) -> Dict[str, Any]:
    return {
        "request_id": record.request_id,
        "approval_status": record.approval_status,
        "approved": record.approved,
        "rejected": record.rejected,
        "approved_by": record.approved_by,
        "rejected_by": record.rejected_by,
        "reason": record.reason,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "rollout_execution_allowed": record.rollout_execution_allowed,
        "rollout_execution_performed": record.rollout_execution_performed,
    }


def _rollout_event_to_dict(record: PlatformModuleRolloutEvent) -> Dict[str, Any]:
    return {
        "request_id": record.request_id,
        "action": record.action,
        "status": record.status,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "details": _loads_json(record.details_json, {}),
    }


def next_self_build_module_request_id(db: Optional[Session] = None) -> str:
    owns_session = db is None
    session = db or _session_scope()
    try:
        latest = (
            session.query(PlatformSelfBuildModuleRequest)
            .order_by(PlatformSelfBuildModuleRequest.id.desc())
            .first()
        )
        if not latest:
            return "module-request-0001"
        try:
            number = int((latest.request_id or "").rsplit("-", 1)[-1]) + 1
        except ValueError:
            number = latest.id + 1
        return f"module-request-{number:04d}"
    finally:
        if owns_session:
            session.close()


def record_self_build_module_request(record: Dict[str, Any]) -> Dict[str, Any]:
    session = _session_scope()
    try:
        model = PlatformSelfBuildModuleRequest(
            request_id=record["request_id"],
            status=record.get("status") or "request_recorded",
            requested_by=record.get("requested_by") or "platform_admin",
            module_name=record.get("module_name") or "Untitled Module",
            module_goal=record.get("module_goal") or "",
            acceptance_criteria_json=_dumps_json(record.get("acceptance_criteria") or []),
            notes=record.get("notes") or "",
            workflow_run_id=record.get("workflow_run_id"),
            handoff_status=record.get("handoff_status") or "waiting_for_app_build_workflow",
            linked_by=record.get("linked_by"),
        )
        session.add(model)
        session.commit()
        session.refresh(model)
        return _request_to_dict(model)
    finally:
        session.close()


def update_self_build_module_request(request_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    session = _session_scope()
    try:
        model = (
            session.query(PlatformSelfBuildModuleRequest)
            .filter(PlatformSelfBuildModuleRequest.request_id == request_id)
            .first()
        )
        if not model:
            return None
        for field in ["status", "workflow_run_id", "handoff_status", "linked_by"]:
            if field in updates:
                setattr(model, field, updates[field])
        if "acceptance_criteria" in updates:
            model.acceptance_criteria_json = _dumps_json(updates.get("acceptance_criteria") or [])
        if "notes" in updates:
            model.notes = updates.get("notes") or ""
        model.updated_at = utc_now()
        session.commit()
        session.refresh(model)
        return _request_to_dict(model)
    finally:
        session.close()


def add_self_build_module_request_event(
    request_id: str,
    action: str,
    status: Optional[str],
    workflow_run_id: Optional[str],
    module_name: Optional[str],
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    session = _session_scope()
    try:
        event = PlatformSelfBuildModuleRequestEvent(
            request_id=request_id,
            action=action,
            status=status,
            workflow_run_id=workflow_run_id,
            module_name=module_name,
            details_json=_dumps_json(details or {}),
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        return _request_event_to_dict(event)
    finally:
        session.close()


def get_self_build_module_request_record(request_id: str) -> Optional[Dict[str, Any]]:
    session = _session_scope()
    try:
        model = (
            session.query(PlatformSelfBuildModuleRequest)
            .filter(PlatformSelfBuildModuleRequest.request_id == request_id)
            .first()
        )
        return _request_to_dict(model) if model else None
    finally:
        session.close()


def list_self_build_module_request_records() -> List[Dict[str, Any]]:
    session = _session_scope()
    try:
        models = (
            session.query(PlatformSelfBuildModuleRequest)
            .order_by(PlatformSelfBuildModuleRequest.created_at.desc(), PlatformSelfBuildModuleRequest.id.desc())
            .all()
        )
        return [_request_to_dict(model) for model in models]
    finally:
        session.close()


def list_self_build_module_request_events(request_id: str) -> List[Dict[str, Any]]:
    session = _session_scope()
    try:
        models = (
            session.query(PlatformSelfBuildModuleRequestEvent)
            .filter(PlatformSelfBuildModuleRequestEvent.request_id == request_id)
            .order_by(PlatformSelfBuildModuleRequestEvent.id.asc())
            .all()
        )
        return [_request_event_to_dict(model) for model in models]
    finally:
        session.close()


def upsert_module_rollout_decision(record: Dict[str, Any]) -> Dict[str, Any]:
    session = _session_scope()
    try:
        model = (
            session.query(PlatformModuleRolloutDecision)
            .filter(PlatformModuleRolloutDecision.request_id == record["request_id"])
            .first()
        )
        if not model:
            model = PlatformModuleRolloutDecision(request_id=record["request_id"])
            session.add(model)
        model.approval_status = record.get("approval_status") or "rollout_rejected"
        model.approved = bool(record.get("approved"))
        model.rejected = bool(record.get("rejected"))
        model.approved_by = record.get("approved_by")
        model.rejected_by = record.get("rejected_by")
        model.reason = record.get("reason") or ""
        model.rollout_execution_allowed = False
        model.rollout_execution_performed = False
        model.updated_at = utc_now()
        session.commit()
        session.refresh(model)
        return _rollout_decision_to_dict(model)
    finally:
        session.close()


def get_module_rollout_decision(request_id: str) -> Optional[Dict[str, Any]]:
    session = _session_scope()
    try:
        model = (
            session.query(PlatformModuleRolloutDecision)
            .filter(PlatformModuleRolloutDecision.request_id == request_id)
            .first()
        )
        return _rollout_decision_to_dict(model) if model else None
    finally:
        session.close()


def add_module_rollout_event(
    request_id: str,
    action: str,
    status: str,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    session = _session_scope()
    try:
        event = PlatformModuleRolloutEvent(
            request_id=request_id,
            action=action,
            status=status,
            details_json=_dumps_json(details or {}),
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        return _rollout_event_to_dict(event)
    finally:
        session.close()


def list_module_rollout_events(request_id: str) -> List[Dict[str, Any]]:
    session = _session_scope()
    try:
        models = (
            session.query(PlatformModuleRolloutEvent)
            .filter(PlatformModuleRolloutEvent.request_id == request_id)
            .order_by(PlatformModuleRolloutEvent.id.asc())
            .all()
        )
        return [_rollout_event_to_dict(model) for model in models]
    finally:
        session.close()


def reset_v82_persistent_state_for_check() -> None:
    session = _session_scope()
    try:
        session.query(PlatformModuleRolloutEvent).delete()
        session.query(PlatformModuleRolloutDecision).delete()
        session.query(PlatformSelfBuildModuleRequestEvent).delete()
        session.query(PlatformSelfBuildModuleRequest).delete()
        session.commit()
    finally:
        session.close()
