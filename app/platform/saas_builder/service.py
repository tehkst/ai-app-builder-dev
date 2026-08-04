from __future__ import annotations

import hashlib
from typing import Any

from app.platform.operating_console.mission_run_service import accept_mission_run, load_mission_run
from app.platform.runtime.provider_router import default_model, selected_provider
from app.platform.saas_builder.lifecycle import project_lifecycle
from app.platform.saas_builder.specification import bounded_specification


def build_status() -> dict[str, Any]:
    return {
        "contract": "saas-builder-v1", "status": "available",
        "reference_application": "appointment_booking",
        "mission_authority": "PlatformWorkflowRun",
        "founder_controls_visible": False,
    }


def create_build(payload: dict[str, Any], user: Any) -> dict[str, Any]:
    description = str(payload.get("description") or "")
    name = str(payload.get("application_name") or "")
    try:
        spec = bounded_specification(description, name)
    except ValueError as exc:
        return {"status": "clarification_required", "message": str(exc)}
    user_id = str(user.id)
    identity = hashlib.sha256(("%s:%s" % (user_id, spec["founder_request"])).encode()).hexdigest()[:12].upper()
    application_id = "APP-%s" % identity
    mission_id = "MISSION-SAAS-%s" % identity
    provider = selected_provider(str(payload.get("provider") or ""))
    context = {
        "action_context_id": "SAAS-BUILD-%s" % identity,
        "mission_id": mission_id, "originating_mission_id": mission_id,
        "title": spec["product_name"], "founder_request": spec["founder_request"],
        "scope": {
            "objective": "Deliver %s as a live appointment-booking SaaS." % spec["product_name"],
            "acceptance_criteria": spec["acceptance_criteria"],
            "in_scope": spec["functional_requirements"],
            "out_of_scope": spec["excluded_functionality"],
            "governance_boundaries": ["Repository, merge, and deployment remain governed."],
        },
        "request_channel": "saas_builder", "application_id": application_id,
        "application_name": spec["product_name"], "workspace_id": "WORKSPACE-%s" % identity,
        "workspace_owner_id": user_id, "source_directory": "generated_apps/%s" % application_id.lower(),
        "service_name": "afos-app-%s" % identity.lower(),
        "repository": "tehkst/ai-app-builder-dev",
        "provider": provider, "model": default_model(provider), "provider_source": "runtime-provider-router",
        "build_summary": "Appointment booking with owner authentication, services, and public bookings.",
    }
    approval = {
        "status": "approved", "decision": "approved", "mission_id": mission_id,
        "approval": {"decision": "approved", "mission_id": mission_id, "approved_by": user.email},
        "scope": "bounded_reference_application",
    }
    result = accept_mission_run(
        context=context, signature="saas-builder-v1:%s" % identity,
        approval=approval, token=str(payload.get("access_token") or ""),
    )
    state = load_mission_run(str(result.get("workflow_run_id") or ""))
    return {"status": "build_started", "build": project_lifecycle(state), "specification": spec}


def get_build(workflow_run_id: str, user: Any) -> dict[str, Any]:
    state = load_mission_run(workflow_run_id)
    context = state.get("context") if isinstance(state.get("context"), dict) else {}
    if not state.get("found") or context.get("request_channel") != "saas_builder":
        return {"status": "not_found"}
    if str(context.get("workspace_owner_id")) != str(user.id):
        return {"status": "forbidden"}
    return {"status": "ok", "build": project_lifecycle(state)}


def delete_build(workflow_run_id: str, user: Any) -> dict[str, Any]:
    """Customer self-service permanent deletion of their own saas_builder project - both the
    real Cloud Run service (if one was ever deployed) and every DB row. Ownership-checked the
    same way get_build already is; no separate founder approval-phrase entry is required from
    the customer (an ordinary SaaS account-closure capability, not a platform governance
    action) - the underlying infrastructure mutation still runs through approved_cloud_run.py's
    real governance gate, using a narrow system-issued token (see
    auth.service.issue_system_governance_token) so it stays uniformly audited.
    """
    state = load_mission_run(workflow_run_id)
    context = state.get("context") if isinstance(state.get("context"), dict) else {}
    if not state.get("found") or context.get("request_channel") != "saas_builder":
        return {"status": "not_found"}
    if str(context.get("workspace_owner_id")) != str(user.id):
        return {"status": "forbidden"}

    from app.platform.auth.service import issue_system_governance_token
    from app.platform.deployment.approved_cloud_run import TEARDOWN_APPROVAL_PHRASE, execute_cloud_run_teardown
    from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
    from app.platform.services.saas_builder_project_teardown_service import (
        delete_saas_builder_project_records,
        find_saas_builder_deployment_identity,
    )

    create_platform_tables()
    db = PlatformSessionLocal()
    try:
        identity = find_saas_builder_deployment_identity(db, workflow_run_id=workflow_run_id)
        teardown_result = None
        if identity.get("found") and identity.get("deployed"):
            teardown_result = execute_cloud_run_teardown(
                {
                    "service_name": identity["service_name"],
                    "region": identity.get("region"),
                    "project_id": identity.get("project_id"),
                    "live_execution": True,
                    "approval_phrase": TEARDOWN_APPROVAL_PHRASE,
                    "token": issue_system_governance_token("saas_builder_customer_self_service_teardown"),
                    "actor": "mission_control",
                    "requested_action": "saas_builder_customer_self_service_teardown",
                }
            )
            if teardown_result.get("status") != "teardown-completed":
                return {"status": "cloud_run_teardown_failed", "detail": teardown_result}
        db_result = delete_saas_builder_project_records(db, workflow_run_id=workflow_run_id)
    finally:
        db.close()

    return {
        "status": "deleted",
        "workflow_run_id": workflow_run_id,
        "cloud_run_teardown": teardown_result,
        "database": db_result,
    }


def diagnose_project_ownership(payload: dict[str, Any]) -> dict[str, Any]:
    """Founder-only, read-only diagnostic: list every saas_builder mission run's stored
    workspace_owner_id next to every registered user's real id/email, so a mismatch
    between "who a project is stored as owned by" and "a user's current account id"
    can be seen directly instead of guessed at. Temporary - remove once the SaaS
    Portal project list has been confirmed correct against real production data.
    """

    from app.platform.auth.service import require_founder

    founder = require_founder(payload)
    if not founder.get("authorized"):
        return {"authorized": False}

    from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
    from app.platform.persistence.models import PlatformWorkflowRun
    from app.platform.services.workflow_run_persistence_service import get_workflow_run_detail

    create_platform_tables()
    db = PlatformSessionLocal()
    try:
        rows = db.query(PlatformWorkflowRun).order_by(PlatformWorkflowRun.created_at.desc()).all()
        builds: list[dict[str, Any]] = []
        for row in rows:
            detail = get_workflow_run_detail(db, workflow_run_id=row.workflow_run_id)
            mission_state = None
            for step in detail.get("steps") or []:
                handler_result = step.get("handler_result")
                if step.get("step_id") == "mission_run_state" and isinstance(handler_result, dict):
                    mission_state = handler_result
                    break
            if not mission_state:
                continue
            context = mission_state.get("context") or {}
            if context.get("request_channel") != "saas_builder":
                continue
            builds.append(
                {
                    "workflow_run_id": row.workflow_run_id,
                    "application_name": context.get("application_name"),
                    "workspace_owner_id": context.get("workspace_owner_id"),
                    "created_at": detail.get("created_at"),
                }
            )
    finally:
        db.close()

    users = _load_users_sync()

    return {"authorized": True, "saas_builder_builds": builds, "users": users}


_sync_user_engine = None


def _load_users_sync() -> list[dict[str, Any]]:
    """Reads the users table with a dedicated sync engine rather than the shared
    module-level async engine - that engine is bound to the uvicorn event loop from
    the first async call made on it, and this diagnostic runs in a threadpool worker,
    so asyncio.run() here would attach a second loop to those connections and fail.
    """

    global _sync_user_engine

    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    from app.core.database import DATABASE_URL
    from app.core.database_urls import normalize_sync_database_url
    from app.models.user import User

    if _sync_user_engine is None:
        _sync_user_engine = create_engine(normalize_sync_database_url(DATABASE_URL), future=True, pool_pre_ping=True)

    with Session(_sync_user_engine) as db:
        rows = db.execute(select(User)).scalars().all()
        return [{"id": row.id, "email": row.email} for row in rows]


def list_builds_for_user(user_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """Return every saas_builder mission run owned by this user.

    There is no dedicated table/index for this - mission run state is stashed inside
    a step's handler_result (see load_mission_run), so this scans every workflow run
    and filters in Python. Fine at today's scale; revisit if PlatformWorkflowRun grows
    large enough that this becomes slow.
    """

    from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
    from app.platform.persistence.models import PlatformWorkflowRun
    from app.platform.services.workflow_run_persistence_service import get_workflow_run_detail

    create_platform_tables()
    db = PlatformSessionLocal()
    try:
        rows = db.query(PlatformWorkflowRun).order_by(PlatformWorkflowRun.created_at.desc()).all()
        results: list[dict[str, Any]] = []
        for row in rows:
            detail = get_workflow_run_detail(db, workflow_run_id=row.workflow_run_id)
            mission_state = None
            for step in detail.get("steps") or []:
                handler_result = step.get("handler_result")
                if step.get("step_id") == "mission_run_state" and isinstance(handler_result, dict):
                    mission_state = handler_result
                    break
            if not mission_state:
                continue
            context = mission_state.get("context") or {}
            if context.get("request_channel") != "saas_builder":
                continue
            if str(context.get("workspace_owner_id")) != str(user_id):
                continue
            project = project_lifecycle(mission_state)
            project["created_at"] = detail.get("created_at")
            project["updated_at"] = detail.get("updated_at")
            results.append(project)
            if len(results) >= limit:
                break
        return results
    finally:
        db.close()
