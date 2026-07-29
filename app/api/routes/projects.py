from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.dependencies import get_current_user
from app.models.user import User
from app.platform.agents.app_build_request_run_check import run_app_build_request
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.services.customer_app_scope_service import draft_customer_app_scope
from app.platform.services.scoping_persistence_service import (
    approve_scoping_record,
    get_scoping_record,
    list_scoping_records_for_user,
    list_scoping_version_chain,
    persist_scoping_analysis,
    serialize_scoping_record,
)
from app.platform.services.scoping_version_rollback_service import (
    rollback_generated_files_to_scoping_version,
)
from app.platform.services.workflow_run_persistence_service import (
    get_workflow_run_detail,
)

router = APIRouter()

REQUEST_KIND = "customer_app"


def _project_name(record: Dict[str, Any]) -> str:
    app_idea = str((record.get("normalized_request") or {}).get("app_idea") or "").strip()
    if not app_idea:
        return "Untitled project"
    return app_idea if len(app_idea) <= 60 else app_idea[:57].rstrip() + "..."


def _build_summary(db, workflow_run_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not workflow_run_id:
        return None
    detail = get_workflow_run_detail(db, workflow_run_id=workflow_run_id)
    if not detail.get("found"):
        return None
    return {
        "workflow_run_id": detail.get("workflow_run_id"),
        "status": detail.get("status"),
        "plan_status": detail.get("plan_status"),
        "step_count": detail.get("step_count"),
        "completed_step_count": detail.get("completed_step_count"),
        "failed_step_count": detail.get("failed_step_count"),
    }


class DraftScopeRequest(BaseModel):
    app_request: str = Field(..., min_length=1)


class AmendScopeRequest(BaseModel):
    app_request: str = Field(..., min_length=1)


class BuildRequest(BaseModel):
    workflow_name: Optional[str] = None


def _owned_record(scoping_request_id: str, current_user: User) -> Dict[str, Any]:
    create_platform_tables()
    db = PlatformSessionLocal()
    try:
        record_model = get_scoping_record(db, scoping_request_id)
        if record_model is None:
            raise HTTPException(status_code=404, detail="Scope not found")
        if record_model.requested_by != str(current_user.id):
            raise HTTPException(status_code=403, detail="You do not have access to this scope")
        return serialize_scoping_record(record_model)
    finally:
        db.close()


@router.get("")
def list_projects(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """List this user's projects (one entry per SOW chain, latest version only)."""

    create_platform_tables()
    db = PlatformSessionLocal()
    try:
        records = list_scoping_records_for_user(db, requested_by=str(current_user.id))
        projects = [
            {
                "scoping_request_id": record["scoping_request_id"],
                "name": _project_name(record),
                "status": record["status"],
                "approval_status": record["approval_status"],
                "version": record["version"],
                "created_at": record["created_at"],
                "updated_at": record["updated_at"],
                "build": _build_summary(db, record.get("workflow_run_id")),
            }
            for record in records
        ]
    finally:
        db.close()

    return {"success": True, "projects": projects}


@router.post("/draft-scope")
def draft_scope(
    request: DraftScopeRequest,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Draft a scope of work (SOW) for a 'build me X' request, for the user to review and approve."""

    result = draft_customer_app_scope(request.app_request)
    if not result.get("success"):
        return result

    create_platform_tables()
    db = PlatformSessionLocal()
    try:
        record = persist_scoping_analysis(
            db,
            result=result,
            llm_result={"status": "not_applicable"},
            requested_by=str(current_user.id),
            request_kind=REQUEST_KIND,
        )
    finally:
        db.close()

    return {**result, **record, "success": True}


@router.post("/{scoping_request_id}/amend")
def amend_scope(
    scoping_request_id: str,
    request: AmendScopeRequest,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Draft a new version of a SOW as a change request against a version you already approved."""

    _owned_record(scoping_request_id, current_user)

    result = draft_customer_app_scope(request.app_request)
    if not result.get("success"):
        return result

    db = PlatformSessionLocal()
    try:
        record = persist_scoping_analysis(
            db,
            result=result,
            llm_result={"status": "not_applicable"},
            requested_by=str(current_user.id),
            request_kind=REQUEST_KIND,
            previous_scoping_request_id=scoping_request_id,
        )
    finally:
        db.close()

    return {**result, **record, "success": True}


@router.post("/{scoping_request_id}/approve")
def approve_scope(
    scoping_request_id: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    _owned_record(scoping_request_id, current_user)

    db = PlatformSessionLocal()
    try:
        record = approve_scoping_record(db, scoping_request_id=scoping_request_id, approved_by=str(current_user.id))
    finally:
        db.close()

    if record is None:
        raise HTTPException(status_code=404, detail="Scope not found")
    return {"success": True, **record}


@router.post("/{scoping_request_id}/build")
def build_scope(
    scoping_request_id: str,
    request: Optional[BuildRequest] = None,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Start a build against an approved scope of work."""

    record = _owned_record(scoping_request_id, current_user)
    request = request or BuildRequest()
    app_request = (record.get("normalized_request") or {}).get("app_idea") or ""

    return run_app_build_request(
        app_request=app_request,
        scoping_request_id=scoping_request_id,
        workflow_name=request.workflow_name,
    )


@router.post("/{scoping_request_id}/rollback")
def rollback_scope(
    scoping_request_id: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Restore generated files to the state they were in for this SOW version."""

    _owned_record(scoping_request_id, current_user)

    db = PlatformSessionLocal()
    try:
        return rollback_generated_files_to_scoping_version(
            db,
            scoping_request_id=scoping_request_id,
            restored_by=str(current_user.id),
        )
    finally:
        db.close()


@router.get("/{scoping_request_id}")
def get_scope(
    scoping_request_id: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    record = _owned_record(scoping_request_id, current_user)
    db = PlatformSessionLocal()
    try:
        build = _build_summary(db, record.get("workflow_run_id"))
    finally:
        db.close()
    return {"success": True, "build": build, **record}


@router.get("/{scoping_request_id}/versions")
def get_scope_versions(
    scoping_request_id: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    _owned_record(scoping_request_id, current_user)

    db = PlatformSessionLocal()
    try:
        chain = list_scoping_version_chain(db, scoping_request_id)
    finally:
        db.close()

    return {"success": bool(chain), "versions": chain}
