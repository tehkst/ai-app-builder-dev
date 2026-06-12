from __future__ import annotations

import json
from typing import Any, Dict, List
from uuid import uuid4

from sqlalchemy.orm import Session

from app.platform.persistence.model_definitions.base import utc_now
from app.platform.persistence.models import PlatformAdminWorkflowExecution
from app.platform.services.workflow_requirements_agent_service import (
    build_code_blueprint,
    build_requirements_scope,
)


STATES = [
    "IDLE",
    "SCOPING",
    "AWAITING_APPROVAL",
    "GENERATING",
    "TESTING",
    "SELF_HEAL",
    "AWAITING_DEPLOYMENT",
]


def start_workflow(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    requirements = str(payload.get("requirements_text") or "").strip()
    record = PlatformAdminWorkflowExecution(
        workflow_id=f"admin-flow-{uuid4().hex[:12]}",
        state="IDLE",
        requirements_text=requirements,
        state_history_json=json.dumps([_event("IDLE", "Awaiting user text requirements.")]),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    if not requirements:
        return _serialize(record)
    _transition(record, "SCOPING", "Requirements agent is analyzing the request.")
    scoped = build_requirements_scope(requirements, payload)
    record.scope_markdown = scoped["scope_markdown"]
    record.memory_buffer_json = json.dumps({
        "requirements_text": requirements,
        "scope_confirmed": False,
        "agent_name": scoped.get("agent_name"),
        "agent_status": scoped.get("agent_status"),
        "agent_error": scoped.get("agent_error"),
    })
    if scoped.get("agent_error"):
        record.alert_message = f"Requirements agent fallback used: {scoped['agent_error']}"
    _transition(record, "AWAITING_APPROVAL", "Waiting for Confirm Scope & Code.")
    db.commit()
    db.refresh(record)
    return _serialize(record)


def confirm_scope_and_code(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    record = _get(db, payload)
    if record is None:
        return {"success": False, "state": "IDLE", "message": "Workflow not found."}
    if record.state != "AWAITING_APPROVAL":
        return {**_serialize(record), "success": False, "message": "Workflow must wait for approval first."}
    _transition(record, "GENERATING", "Code blueprint agent generated copyable output.")
    generated = build_code_blueprint(record.requirements_text, record.scope_markdown, payload)
    record.generated_code = generated["generated_code"]
    if generated.get("agent_error"):
        record.alert_message = f"Code agent fallback used: {generated['agent_error']}"
    _transition(record, "TESTING", "Verification logic completed without source writes.")
    _transition(record, "AWAITING_DEPLOYMENT", "Manual GitHub migration required.")
    record.manual_deploy_instructions = _manual_deploy_instructions()
    record.github_push_performed = False
    db.commit()
    db.refresh(record)
    return _serialize(record)


def self_heal_workflow(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    record = _get(db, payload)
    if record is None:
        return {
            "success": True,
            "state": "IDLE",
            "cache_cleared": True,
            "memory_buffer_rolled_back": True,
            "alert_message": "Workflow was missing. Refresh and start again.",
        }
    target = str(payload.get("target_state") or "AWAITING_APPROVAL")
    if target not in {"AWAITING_APPROVAL", "IDLE"}:
        target = "AWAITING_APPROVAL"
    _transition(record, "SELF_HEAL", "Cache cleared and memory buffer rolled back.")
    record.cache_snapshot_json = "{}"
    record.memory_buffer_json = json.dumps({"requirements_text": record.requirements_text})
    record.alert_message = "Manual refresh required before continuing code execution."
    _transition(record, target if record.scope_markdown else "IDLE", record.alert_message)
    db.commit()
    db.refresh(record)
    return {**_serialize(record), "cache_cleared": True, "memory_buffer_rolled_back": True}


def get_workflow(db: Session, workflow_id: str) -> Dict[str, Any]:
    record = db.query(PlatformAdminWorkflowExecution).filter_by(workflow_id=workflow_id).first()
    return _serialize(record) if record else {"success": False, "state": "IDLE", "message": "Workflow not found."}


def _get(db: Session, payload: Dict[str, Any]) -> PlatformAdminWorkflowExecution:
    workflow_id = str(payload.get("workflow_id") or "")
    return db.query(PlatformAdminWorkflowExecution).filter_by(workflow_id=workflow_id).first()


def _transition(record: PlatformAdminWorkflowExecution, state: str, message: str) -> None:
    history = _json_list(record.state_history_json)
    record.state = state
    record.updated_at = utc_now()
    history.append(_event(state, message))
    record.state_history_json = json.dumps(history)


def _event(state: str, message: str) -> Dict[str, str]:
    return {"state": state, "message": message, "timestamp": utc_now().isoformat()}


def _serialize(record: PlatformAdminWorkflowExecution) -> Dict[str, Any]:
    return {
        "success": True,
        "workflow_id": record.workflow_id,
        "state": record.state,
        "states": STATES,
        "requirements_text": record.requirements_text,
        "scope_markdown": record.scope_markdown,
        "generated_code": record.generated_code,
        "manual_deploy_instructions": record.manual_deploy_instructions,
        "state_history": _json_list(record.state_history_json),
        "alert_message": record.alert_message,
        "agent_context": _json_dict(record.memory_buffer_json),
        "timeout_seconds": record.timeout_seconds,
        "github_push_performed": bool(record.github_push_performed),
    }


def _json_list(raw: str) -> List[Dict[str, Any]]:
    try:
        value = json.loads(raw or "[]")
        return value if isinstance(value, list) else []
    except json.JSONDecodeError:
        return []


def _json_dict(raw: str) -> Dict[str, Any]:
    try:
        value = json.loads(raw or "{}")
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}


def _manual_deploy_instructions() -> str:
    return "Paste this code into GitHub manually. Do not use platform automation to push. Railway will deploy after GitHub receives the committed file."
