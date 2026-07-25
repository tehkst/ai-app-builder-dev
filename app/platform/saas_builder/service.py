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
