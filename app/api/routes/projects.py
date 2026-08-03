from __future__ import annotations

import json
import queue
import threading
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.api.dependencies import get_current_user, get_current_user_from_query_or_header
from app.models.user import User
from app.platform.agents.app_build_request_run_check import resume_app_build_request, run_app_build_request
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.services.approval_service import decide_approval
from app.platform.services.customer_app_fix_service import apply_customer_reported_fix
from app.platform.services.customer_app_scope_service import draft_customer_app_scope
from app.platform.services.generated_app_preview_service import render_generated_app_preview
from app.platform.services.scoping_persistence_service import (
    approve_scoping_record,
    delete_scoping_chain,
    get_scoping_record,
    list_scoping_records_for_user,
    list_scoping_version_chain,
    persist_scoping_analysis,
    request_publish_for_scoping_record,
    serialize_scoping_record,
)
from app.platform.services.scoping_version_rollback_service import (
    rollback_generated_files_to_scoping_version,
)
from app.platform.services.workflow_run_persistence_service import (
    get_workflow_run_detail,
)
from app.platform.services.workflow_step_approval_service import get_step_approval_request

router = APIRouter()

REQUEST_KIND = "customer_app"


def _project_name(record: Dict[str, Any]) -> str:
    app_idea = str((record.get("normalized_request") or {}).get("app_idea") or "").strip()
    if not app_idea:
        return "Untitled project"
    return app_idea if len(app_idea) <= 60 else app_idea[:57].rstrip() + "..."


def _step_failure_message(step: Dict[str, Any]) -> Optional[str]:
    """Best-effort human-readable reason for a failed/blocked/escalated step.

    get_workflow_run_detail already carries the real diagnostic, it was just never
    forwarded past _build_summary, which left founders staring at a bare red X with
    no way to tell a provider-config problem from anything else. Never fabricates a
    reason: returns None if nothing real is available.

    A step's handler_result top-level key (set from step.output_json) is only
    populated on success - on failure/escalation the executor writes the bridge
    result into step.error_json instead, nested under
    error.bridge_result.handler_result, which is where a management-agent's
    decision "message"/"rationale" actually live.
    """
    if step.get("status") not in {"failed", "blocked", "escalated"}:
        return None

    def _combined(handler_result: Dict[str, Any]) -> Optional[str]:
        # "message" is a terse verdict label; "rationale" is the actual reasoning -
        # combine both when present so this reads as a real explanation.
        message = handler_result.get("message")
        rationale = handler_result.get("rationale")
        if message and rationale:
            return f"{message} {rationale}"
        if message or rationale:
            return str(message or rationale)
        return None

    combined = _combined(step.get("handler_result") or {})
    if combined:
        return combined
    error = step.get("error") or {}
    if isinstance(error, dict):
        nested_handler_result = ((error.get("bridge_result") or {}).get("handler_result")) or {}
        combined = _combined(nested_handler_result)
        if combined:
            return combined
        if error.get("error"):
            return str(error["error"])
    return None


def _step_decision_detail(step: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The full decision data a founder needs to actually act on an escalated step -
    not just a display message. Real, structural data only (decision/concerns/
    redirect_instructions come straight from the management agent's own response);
    never fabricated when a step didn't escalate."""
    if step.get("status") != "escalated":
        return None
    error = step.get("error") or {}
    handler_result = ((error.get("bridge_result") or {}).get("handler_result")) or {}
    if not handler_result:
        return None
    return {
        "decision": handler_result.get("decision"),
        "rationale": handler_result.get("rationale"),
        "concerns": handler_result.get("concerns") or [],
        "redirect_instructions": handler_result.get("redirect_instructions"),
    }


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
        "created_at": detail.get("created_at"),
        "completed_at": detail.get("completed_at"),
        "steps": [
            {
                "step_run_id": step.get("step_run_id"),
                "title": step.get("title"),
                "status": step.get("status"),
                "message": _step_failure_message(step),
                "decision": _step_decision_detail(step),
                "approval_id": (
                    get_step_approval_request(db, step_run_id=step.get("step_run_id")) or {}
                ).get("approval_id")
                if step.get("status") == "escalated"
                else None,
            }
            for step in detail.get("steps") or []
        ],
    }


MAX_ATTACHMENTS = 5
MAX_ATTACHMENT_TEXT_CHARS = 8000


class AttachmentInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    mime_type: Optional[str] = None
    text_content: Optional[str] = Field(default=None, max_length=40000)


class DraftScopeRequest(BaseModel):
    app_request: str = Field(..., min_length=1)
    attachments: List[AttachmentInput] = Field(default_factory=list)


class AmendScopeRequest(BaseModel):
    app_request: str = Field(..., min_length=1)
    attachments: List[AttachmentInput] = Field(default_factory=list)


class RequestPublishRequest(BaseModel):
    pass


def _augmented_app_request(app_request: str, attachments: List[AttachmentInput]) -> str:
    """Fold attached reference files into the plain-language request sent to the
    scope drafter.

    There's no vision-capable model wired into this platform (see
    app.platform.runtime.ai_provider) - only text can actually reach the model, so
    an attached image contributes its filename as a labeled reference rather than
    real image understanding; attached text-ish files (notes, existing copy, CSVs,
    etc.) contribute their real extracted text, capped so one huge attachment can't
    blow out the scoping prompt.
    """

    if not attachments:
        return app_request
    sections = [app_request, "", "Attached reference files:"]
    for attachment in attachments[:MAX_ATTACHMENTS]:
        text_content = (attachment.text_content or "").strip()
        if text_content:
            capped = text_content[:MAX_ATTACHMENT_TEXT_CHARS]
            sections.append(f"- {attachment.name}: {capped}")
        else:
            sections.append(f"- {attachment.name} (reference file supplied, no extractable text)")
    return "\n".join(sections)


def _attachment_manifest(attachments: List[AttachmentInput]) -> List[Dict[str, Any]]:
    return [
        {"name": attachment.name, "mime_type": attachment.mime_type}
        for attachment in attachments[:MAX_ATTACHMENTS]
    ]


class BuildRequest(BaseModel):
    workflow_name: Optional[str] = None


class ReportBugRequest(BaseModel):
    bug_report: str = Field(..., min_length=3)


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
    """List every project this user owns, across both build pipelines.

    "Project" spans two independent systems today: SOW-drafted builds (this router,
    PlatformScopingRequest) and one-shot /saas-builder builds (PlatformWorkflowRun
    mission runs, see app.platform.saas_builder.service.list_builds_for_user) - the
    latter predates this router and is the only one with a real live_url. Both are
    merged here so a user sees everything they've built in one place.
    """

    create_platform_tables()
    db = PlatformSessionLocal()
    try:
        records = list_scoping_records_for_user(db, requested_by=str(current_user.id))
        projects = [
            {
                "id": record["scoping_request_id"],
                "source": "scoping",
                "name": _project_name(record),
                "status": record["status"],
                "approval_status": record["approval_status"],
                "version": record["version"],
                "created_at": record["created_at"],
                "updated_at": record["updated_at"],
                "build": _build_summary(db, record.get("workflow_run_id")),
                "live_url": None,
            }
            for record in records
        ]
    finally:
        db.close()

    from app.platform.saas_builder.service import list_builds_for_user

    for build in list_builds_for_user(str(current_user.id)):
        projects.append(
            {
                "id": build.get("workflow_run_id"),
                "source": "saas_builder",
                "name": build.get("application_name") or "Untitled project",
                "status": build.get("status"),
                "approval_status": None,
                "version": None,
                "created_at": build.get("created_at"),
                "updated_at": build.get("updated_at"),
                "build": None,
                "live_url": build.get("live_url"),
            }
        )

    projects.sort(key=lambda project: project.get("updated_at") or "", reverse=True)
    return {"success": True, "projects": projects}


@router.post("/draft-scope")
def draft_scope(
    request: DraftScopeRequest,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Draft a scope of work (SOW) for a 'build me X' request, for the user to review and approve."""

    result = draft_customer_app_scope(_augmented_app_request(request.app_request, request.attachments))
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
            attachments=_attachment_manifest(request.attachments),
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

    result = draft_customer_app_scope(_augmented_app_request(request.app_request, request.attachments))
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
            attachments=_attachment_manifest(request.attachments),
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


@router.delete("/{scoping_request_id}")
def delete_scope(
    scoping_request_id: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Delete a SOW-drafted project and every version in its amendment chain.

    Scoped to the scoping pipeline only - saas_builder projects may have a real
    deployed Cloud Run service behind them and deleting those needs its own,
    separate teardown flow rather than just removing a database row.
    """

    _owned_record(scoping_request_id, current_user)

    db = PlatformSessionLocal()
    try:
        deleted = delete_scoping_chain(db, scoping_request_id=scoping_request_id, requested_by=str(current_user.id))
    finally:
        db.close()

    if not deleted:
        raise HTTPException(status_code=404, detail="Scope not found")
    return {"success": True}


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


@router.post("/{scoping_request_id}/build/stream")
def build_scope_stream(
    scoping_request_id: str,
    request: Optional[BuildRequest] = None,
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Same build as /build, but streams each step's real result as it happens.

    Runs the (still fully synchronous, blocking) build pipeline in a background
    thread and relays each on_step_complete callback through a queue as an SSE
    event, so the browser sees each agent's actual decision/rationale the moment
    that step finishes - not a fake "thinking..." animation.
    """

    record = _owned_record(scoping_request_id, current_user)
    request = request or BuildRequest()
    app_request = (record.get("normalized_request") or {}).get("app_idea") or ""

    def event_stream():
        event_queue: "queue.Queue[Optional[Dict[str, Any]]]" = queue.Queue()

        def on_step_complete(event: Dict[str, Any]) -> None:
            event_queue.put(event)

        def worker() -> None:
            try:
                result = run_app_build_request(
                    app_request=app_request,
                    scoping_request_id=scoping_request_id,
                    workflow_name=request.workflow_name,
                    on_step_complete=on_step_complete,
                )
                event_queue.put({"type": "workflow_completed", "result": result})
            except Exception as exc:
                event_queue.put({"type": "error", "error": str(exc)})
            finally:
                event_queue.put(None)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        while True:
            event = event_queue.get()
            if event is None:
                break
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


class StepDecisionRequest(BaseModel):
    action: str = Field(..., pattern="^(approve|reject)$")
    note: Optional[str] = None


@router.post("/{scoping_request_id}/steps/{step_run_id}/decision/stream")
def decide_workflow_step(
    scoping_request_id: str,
    step_run_id: str,
    request: StepDecisionRequest,
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Founder acts on a management-tier escalation, then resumes the build live.

    A real decision (approve/reject), not a display-only acknowledgement - approve
    carries the step forward as completed and continues the remaining steps via
    resume_app_build_request (same workflow_run_id, not a restart); reject ends the
    build. Reuses the exact same background-thread + SSE queue pattern as
    /build/stream, on the same on_step_complete plumbing, so the founder watches the
    remaining steps stream live exactly like the original build - not a second,
    parallel status mechanism.
    """

    record = _owned_record(scoping_request_id, current_user)
    workflow_run_id = record.get("workflow_run_id")
    if not workflow_run_id:
        raise HTTPException(status_code=404, detail="This project has no build to resume")

    db = PlatformSessionLocal()
    try:
        approval = get_step_approval_request(db, step_run_id=step_run_id)
        if approval is None:
            raise HTTPException(status_code=404, detail="No decision is pending for this step")
        action_payload = approval.get("action_payload") or {}
        if action_payload.get("workflow_run_id") != workflow_run_id:
            raise HTTPException(status_code=403, detail="This step does not belong to your project")
        if approval.get("status") != "pending":
            raise HTTPException(status_code=409, detail="This decision was already made")
        step_id = action_payload.get("step_id")

        decide_approval(
            db,
            approval_id=approval["approval_id"],
            new_status="approved" if request.action == "approve" else "rejected",
            approver_id=str(current_user.id),
            decision_note=request.note,
        )
    finally:
        db.close()

    app_request = (record.get("normalized_request") or {}).get("app_idea") or ""
    decision = {"step_id": step_id, "action": request.action, "note": request.note}

    def event_stream():
        event_queue: "queue.Queue[Optional[Dict[str, Any]]]" = queue.Queue()

        def on_step_complete(event: Dict[str, Any]) -> None:
            event_queue.put(event)

        def worker() -> None:
            try:
                result = resume_app_build_request(
                    app_request=app_request,
                    scoping_request_id=scoping_request_id,
                    workflow_run_id=workflow_run_id,
                    decision=decision,
                    on_step_complete=on_step_complete,
                )
                event_queue.put({"type": "workflow_completed", "result": result})
            except Exception as exc:
                event_queue.put({"type": "error", "error": str(exc)})
            finally:
                event_queue.put(None)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        while True:
            event = event_queue.get()
            if event is None:
                break
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/{scoping_request_id}/request-publish")
def request_publish(
    scoping_request_id: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Ask for this completed build to be published.

    Does not deploy anything itself - see request_publish_for_scoping_record for
    why this stays a request a founder reviews rather than an instant self-serve
    action.
    """

    _owned_record(scoping_request_id, current_user)

    db = PlatformSessionLocal()
    try:
        result = request_publish_for_scoping_record(
            db,
            scoping_request_id=scoping_request_id,
            requested_by=str(current_user.id),
        )
    finally:
        db.close()
    return result


@router.get("/{scoping_request_id}/preview.html", response_class=HTMLResponse)
def preview_html(
    scoping_request_id: str,
    current_user: User = Depends(get_current_user_from_query_or_header),
) -> HTMLResponse:
    """Serve a best-effort rendered preview of this build's generated frontend.

    Loaded directly as an <iframe src="...">, so auth comes via
    get_current_user_from_query_or_header rather than the usual bearer-only
    dependency (see that function's docstring).
    """

    record = _owned_record(scoping_request_id, current_user)
    db = PlatformSessionLocal()
    try:
        html = render_generated_app_preview(db, workflow_run_id=record.get("workflow_run_id"))
    finally:
        db.close()
    return HTMLResponse(content=html)


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


@router.post("/{scoping_request_id}/fix")
def fix_scope(
    scoping_request_id: str,
    request: ReportBugRequest,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Fix a bug the customer reports in their already-built project.

    Loads the project's current generated files, asks the model for the smallest
    correct fix plus a required regression test covering the reported scenario,
    and persists the result as the new authoritative files for this project's build.
    """

    _owned_record(scoping_request_id, current_user)

    db = PlatformSessionLocal()
    try:
        return apply_customer_reported_fix(
            db,
            scoping_request_id=scoping_request_id,
            bug_report=request.bug_report,
        )
    finally:
        db.close()


@router.get("/{scoping_request_id}")
def get_scope(
    scoping_request_id: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    if scoping_request_id.startswith("MISSION-RUN-"):
        from app.platform.saas_builder.service import get_build

        result = get_build(scoping_request_id, current_user)
        if result.get("status") == "not_found":
            raise HTTPException(status_code=404, detail="Project not found")
        if result.get("status") == "forbidden":
            raise HTTPException(status_code=403, detail="You do not have access to this project")
        return {"success": True, "source": "saas_builder", **(result.get("build") or {})}

    record = _owned_record(scoping_request_id, current_user)
    db = PlatformSessionLocal()
    try:
        build = _build_summary(db, record.get("workflow_run_id"))
    finally:
        db.close()
    return {"success": True, "source": "scoping", "build": build, **record}


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
