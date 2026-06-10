# Split from the legacy module to keep each Python file under 200 lines.
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
