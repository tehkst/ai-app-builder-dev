from __future__ import annotations

from typing import Any


STAGES = (
    "draft", "clarification_required", "scope_confirmed", "planning", "engineering",
    "validating", "repairing", "ready_for_repository", "repository_execution",
    "deploying", "verifying", "live", "failed", "blocked", "cancelled",
)

MISSION_STAGE_MAP = {
    "accepted": "scope_confirmed",
    "product_definition": "planning",
    "ux_specification": "planning",
    "architecture": "planning",
    "engineering_plan": "engineering",
    "implementation": "validating",
    "repository_approval": "ready_for_repository",
    "change_set_ready": "ready_for_repository",
    "pull_request": "repository_execution",
    "ci_validation": "repository_execution",
    "merge_approval": "repository_execution",
    "deployment_approval": "deploying",
    "production_verification": "verifying",
    "founder_acceptance": "verifying",
    "complete": "live",
}


def project_lifecycle(state: dict[str, Any]) -> dict[str, Any]:
    contract = state.get("delivery_contract") if isinstance(state.get("delivery_contract"), dict) else {}
    mission_stage = str(contract.get("current_stage") or state.get("current_stage") or "draft")
    status = MISSION_STAGE_MAP.get(mission_stage, mission_stage if mission_stage in STAGES else "draft")
    if state.get("status") in {"blocked", "failed"}:
        status = str(state["status"])
    context = state.get("context") if isinstance(state.get("context"), dict) else {}
    deployment = _artifact(contract, "deployment")
    verification = _artifact(contract, "production_verification")
    return {
        "application_id": context.get("application_id"),
        "application_name": context.get("application_name"),
        "workspace_id": context.get("workspace_id"),
        "mission_id": state.get("mission_id"),
        "workflow_run_id": state.get("workflow_run_id"),
        "status": status,
        "mission_stage": mission_stage,
        "progress": _progress(status),
        "message": _message(status),
        "live_url": (deployment.get("content") or {}).get("service_url"),
        "deployment_revision": (deployment.get("content") or {}).get("revision_name"),
        "browser_acceptance": (verification.get("content") or {}).get("browser_acceptance"),
        "build_summary": context.get("build_summary"),
        "founder_controls_visible": False,
    }


def _artifact(contract: dict[str, Any], kind: str) -> dict[str, Any]:
    matches = [item for item in contract.get("artifacts") or [] if item.get("artifact_type") == kind]
    return matches[-1] if matches else {}


def _progress(status: str) -> int:
    order = ["draft", "scope_confirmed", "planning", "engineering", "validating",
             "ready_for_repository", "repository_execution", "deploying", "verifying", "live"]
    return int(100 * order.index(status) / (len(order) - 1)) if status in order else 0


def _message(status: str) -> str:
    return {
        "scope_confirmed": "Scope confirmed. Your build is entering planning.",
        "planning": "The product specification and architecture are being prepared.",
        "engineering": "Your application is being implemented.",
        "validating": "The application is being tested.",
        "repairing": "A bounded repair is in progress.",
        "ready_for_repository": "The validated build is ready for governed repository execution.",
        "repository_execution": "Repository checks and release review are in progress.",
        "deploying": "Your application is being deployed.",
        "verifying": "The live application is completing browser acceptance.",
        "live": "Your application is live.",
        "blocked": "The build needs founder review before it can continue.",
        "failed": "The build could not complete. Technical evidence is available to operations.",
    }.get(status, "Your build request has been received.")
