from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.platform.services.persistent_state_store_service import (
    add_self_build_module_request_event,
    update_self_build_module_request,
)
from app.platform.services.scoping_gateway_service import analyze_scoping_request
from app.platform.services.scoping_persistence_service import (
    approve_scoping_record,
    persist_scoping_analysis,
)
from app.platform.services.self_build_module_request_service import (
    create_self_build_module_request,
    get_self_build_module_request,
)


def create_module_requirements_scope(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    module = create_self_build_module_request(
        module_name=payload.get("module_name"),
        module_goal=payload.get("module_goal"),
        requested_by=str(payload.get("requested_by") or "platform_admin"),
        workflow_run_id=payload.get("workflow_run_id"),
        acceptance_criteria=payload.get("acceptance_criteria") or [],
        notes=payload.get("notes"),
        initial_status="pending",
    )
    scope = _persist_scope(db, _scope_payload(module["request"]))
    return _response(module, scope, "review_scope")


def accept_module_requirements_scope(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    request_id = str(payload.get("request_id") or "")
    scoping_request_id = str(payload.get("scoping_request_id") or "")
    scope = approve_scoping_record(db, scoping_request_id=scoping_request_id) if scoping_request_id else None
    record = update_self_build_module_request(request_id, {"status": "scope_accepted"})
    if record:
        _event(request_id, "scope_accepted", record, {"scoping_request_id": scoping_request_id})
    return {
        "success": bool(record and scope),
        "status": "scope_accepted" if record and scope else "not_found",
        "request": record,
        "requirements_scope": scope,
        "generation_started": False,
        "next_required_action": "await_generation_approval",
    }


def reject_module_requirements_scope(payload: Dict[str, Any]) -> Dict[str, Any]:
    request_id = str(payload.get("request_id") or "")
    reason = str(payload.get("reason") or "Rejected by platform admin.")
    record = update_self_build_module_request(request_id, {"status": "scope_rejected", "notes": reason})
    if record:
        _event(request_id, "scope_rejected", record, {"reason": reason})
    return {"success": bool(record), "status": "scope_rejected" if record else "not_found", "request": record}


def amend_module_requirements_scope(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    request_id = str(payload.get("request_id") or "")
    updates = {
        "status": "pending_scope_confirmation",
        "module_name": str(payload.get("module_name") or "Untitled Module").strip(),
        "module_goal": str(payload.get("module_goal") or "").strip(),
        "acceptance_criteria": _list(payload.get("acceptance_criteria")),
    }
    record = update_self_build_module_request(request_id, updates)
    if not record:
        return {"success": False, "status": "not_found", "request": None}
    _event(request_id, "scope_amended", record, {"reason": payload.get("reason")})
    scope = _persist_scope(db, _scope_payload(record))
    return _response(get_self_build_module_request(request_id), scope, "review_amended_scope")


def _persist_scope(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    result = analyze_scoping_request(payload)
    record = persist_scoping_analysis(db, result=result, llm_result={"status": "not_applicable"})
    return {**result, **record, "success": True}


def _scope_payload(record: Dict[str, Any]) -> Dict[str, Any]:
    # target_users/core_views/data_entities are deliberately left blank here (not
    # a fixed placeholder like "Platform Function Builder") so
    # analyze_scoping_request's real LLM-backed drafting derives them from the
    # actual module_name/module_goal below - a real, confirmed bug (Jarvis
    # pipeline simplification, Phase 1 audit) was every module request getting
    # this exact same hardcoded scope regardless of what the module actually was.
    criteria = record.get("acceptance_criteria") or []
    return {
        "mode_selector": "Enhance Platform AI Software Factory",
        "target_boundary": "Current Platform",
        "change_classification": "New Feature",
        "app_idea": f"{record.get('module_name')}: {record.get('module_goal')}",
        "target_users": [],
        "core_views": [],
        "data_entities": [],
        "auth_model": "Platform admin JWT required; internal token fallback is controlled.",
        "success_criteria": criteria,
        "request_constraints": ["DB preview only", "No code execution", "No deployment"],
    }


def _response(module: Dict[str, Any], scope: Dict[str, Any], next_action: str) -> Dict[str, Any]:
    return {**module, "requirements_scope": scope, "next_required_action": next_action, "generation_started": False}


def _event(request_id: str, action: str, record: Dict[str, Any], details: Dict[str, Any]) -> None:
    add_self_build_module_request_event(request_id, action, record.get("status"), record.get("workflow_run_id"), record.get("module_name"), details)


def _list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value or "").split("\n") if item.strip()]
