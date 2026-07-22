from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any

from app.platform.auth.service import require_founder
from app.platform.engineering.change_set_service import generate_executable_change_set
from app.platform.execution.orchestrator import launch_approved_mission_workflow
from app.platform.execution.service import create_execution_mission, record_execution_mission_evidence
from app.platform.founder_approval.service import approve_proposal, reject_proposal
from app.platform.operating_console.mission_run_service import accept_mission_run
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.operational_evidence import record_operational_evidence
from app.platform.services.workflow_run_persistence_service import get_workflow_run_detail, persist_workflow_result


ACTION_ENDPOINT = "/mission-control/operating-console/action"
SAFE_ACTIONS = {"review_scope", "save_mission", "approve_mission", "reject_mission", "continue_planning", "review_changes", "retry_change_set", "review_validation_errors"}


def build_pending_mission_actions(
    founder_request: str,
    *,
    provider: Any = None,
    model: Any = None,
) -> dict[str, Any]:
    context = _mission_context(founder_request, provider=provider, model=model)
    signature = _sign_context(context)
    return _action_metadata(context, signature, "pending_approval")


def build_decision_ready_mission_actions(
    founder_request: str,
    *,
    provider: Any = None,
    model: Any = None,
) -> dict[str, Any]:
    context = _mission_context(founder_request, provider=provider, model=model)
    signature = _sign_context(context)
    shared = {"action_context": context, "context_signature": signature}
    return {
        "intent_type": "decision_ready_mission",
        "recommended_action": "Approve, revise, or reject the recommended mission.",
        "founder_approval_required": True,
        "action_buttons": [
            _button("Approve Mission", "approve_mission", shared),
            {"label": "Edit Scope", "action_type": "function", "target": "editRecommendedScope", "payload": {**shared, "scope_text": context["scope"]["objective"]}},
            _button("Reject", "reject_mission", shared, primary=False),
        ],
    }


def dispatch_board_room_action(payload: dict[str, Any]) -> dict[str, Any]:
    authorized = require_founder(payload)
    if not authorized.get("authorized"):
        return _failure(None, "authorization", "Founder authentication is required.")
    action = str(payload.get("action") or "").strip()
    context = payload.get("action_context") if isinstance(payload.get("action_context"), dict) else {}
    signature = str(payload.get("context_signature") or "")
    if action not in SAFE_ACTIONS:
        return _failure(None, "action_dispatch", "This Board Room action is not supported.")
    if not _valid_context(context, signature):
        return _failure(None, "action_context", "The mission action context is missing, expired, or was changed. Return to the Board Room and request a fresh proposal.")

    state = _load_state(str(context["action_context_id"])) or _pending_state(context)
    if action == "review_scope":
        return _scope_response(context, signature, state)
    if action == "save_mission":
        _persist_state(state)
        return _saved_response(context, signature, state)
    if action == "reject_mission":
        rejection = reject_proposal({
            "proposal_id": context["proposal_id"],
            "request_id": context["request_id"],
            "rejected_by": authorized.get("email") or "Founder",
            "reason": "Founder rejected the Board Room mission recommendation.",
            "persist_repository_artifacts": False,
        })
        state.update({"mission_id": None, "status": "rejected", "approval_status": "rejected", "rejection": rejection.get("approval"), "workflow_run_id": None})
        evidence = record_operational_evidence(
            "board_room_recommendation_decision",
            "founder_approval",
            str(context["action_context_id"]),
            "rejected",
            {"proposal_id": context["proposal_id"], "request_id": context["request_id"], "decision": "rejected", "mission_created": False, "workflow_run_created": False},
        )
        return {
            "status": "rejected",
            "mission_id": None,
            "workflow_run_id": None,
            "decision_evidence": evidence,
            "board_room_response": "Recommendation rejected. No mission or execution workflow was created.",
            "action_metadata": {"intent_type": "rejected", "recommended_action": "Revise the request when you want to reconsider it.", "action_buttons": []},
            "governance": _governance(),
        }
    if action == "review_validation_errors":
        return _validation_errors_response(context, signature, state)
    if action == "continue_planning" and state.get("approval_status") != "approved":
        return _failure(
            str(context["mission_id"]),
            "founder_approval",
            "Approve the displayed mission scope before planning can begin.",
            action_metadata=_action_metadata(context, signature, "pending_approval"),
        )
    if action in {"approve_mission", "continue_planning", "retry_change_set"}:
        return _prepare_approved_mission(payload, context, signature, state, authorized)
    return _changes_response(context, signature, state)


def _prepare_approved_mission(
    payload: dict[str, Any],
    context: dict[str, Any],
    signature: str,
    state: dict[str, Any],
    authorized: dict[str, Any],
) -> dict[str, Any]:
    mission_id = str(context["mission_id"])
    approval = state.get("approval") if isinstance(state.get("approval"), dict) else {}
    if state.get("approval_status") != "approved":
        approval = approve_proposal(
            {
                "proposal_id": context["proposal_id"],
                "request_id": context["request_id"],
                "mission_id": mission_id,
                "approved_by": authorized.get("email") or "Founder",
                "comment": "Founder approved the Board Room mission scope.",
                "acceptance_criteria": context["scope"]["acceptance_criteria"],
                "persist_repository_artifacts": False,
            }
        )
        if approval.get("status") != "approved":
            state.update({"mission_id": mission_id, "approval_status": "blocked", "failed_stage": "founder_approval", "blocked_reason": "Founder Approval did not complete."})
            _persist_state(state)
            return _workflow_response(context, signature, state)
        state.update({"mission_id": mission_id, "approval_status": "approved", "approval": approval, "failed_stage": None, "blocked_reason": None})
        _persist_state(state)

    accepted = accept_mission_run(
        context=context,
        signature=signature,
        approval=approval,
        token=str(payload.get("token") or ""),
    )
    state.update({"status": accepted.get("status"), "workflow_run_id": accepted.get("workflow_run_id"), "failed_stage": accepted.get("error", {}).get("classification") if accepted.get("status") == "blocked" else None, "blocked_reason": accepted.get("message") if accepted.get("status") == "blocked" else None})
    _persist_state(state)
    return {
        **accepted,
        "board_room_response": accepted["message"],
        "action_metadata": {
            "intent_type": "mission_run",
            "recommended_action": "Configure shared platform persistence before starting durable mission work." if accepted.get("status") == "blocked" else "Monitor mission progress.",
            "founder_approval_required": False,
            "action_buttons": [],
        },
    }


def _restore_execution_evidence(payload: dict[str, Any], context: dict[str, Any], state: dict[str, Any]) -> None:
    mission_id = str(context["mission_id"])
    create_execution_mission({"token": payload.get("token"), "mission_id": mission_id, "founder_request": context["founder_request"], "title": context["title"]})
    workflow = state.get("workflow") if isinstance(state.get("workflow"), dict) else {}
    for key, value in (
        ("approved_scope", context.get("scope")),
        ("founder_approval", state.get("approval")),
        ("planning_result", workflow.get("planning_result")),
        ("architecture_review", workflow.get("architecture_review")),
        ("engineering_handoff", workflow.get("engineering_handoff")),
        ("executable_change_set", state.get("change_set")),
    ):
        if isinstance(value, dict) and value:
            record_execution_mission_evidence(mission_id, key, value)


def _mission_context(founder_request: str, *, provider: Any, model: Any) -> dict[str, Any]:
    request = " ".join(founder_request.split()).strip()
    fingerprint = hashlib.sha256(request.encode("utf-8")).hexdigest()[:12].upper()
    mission_id = f"MISSION-{fingerprint}"
    return {
        "action_context_id": f"BOARD-ACTION-{fingerprint}",
        "proposal_id": f"PROP-{fingerprint}",
        "request_id": f"REQ-{fingerprint}",
        "mission_id": mission_id,
        "originating_mission_id": mission_id,
        "original_mission_id": mission_id,
        "title": _title(request),
        "founder_request": request,
        "scope": _scope(request),
        "provider": str(provider or "") or None,
        "model": str(model or "") or None,
        "governance_version": "MC-ACTION-01",
    }


def _scope(request: str) -> dict[str, Any]:
    return {
        "objective": request,
        "acceptance_criteria": [
            "The requested founder outcome is implemented within the approved scope.",
            "Existing governance and authentication boundaries remain intact.",
            "The proposed changes pass the mission validation plan before repository execution is authorized.",
        ],
        "in_scope": ["Prepare one canonical mission", "Generate a mission-specific plan and engineering handoff", "Prepare a repository-grounded executable change set"],
        "out_of_scope": ["Repository file writes", "Branch, commit, push, or pull request creation", "Merge, deployment, rollback, or traffic shift"],
        "governance_boundaries": ["Mission approval authorizes safe preparation only", "Repository execution requires the exact GitHub execution approval contract", "Merge and production actions retain their separate founder approvals"],
        "expected_next_action": "Founder reviews and approves this scope before planning begins.",
    }


def _pending_state(context: dict[str, Any]) -> dict[str, Any]:
    return {"action_context_id": context["action_context_id"], "mission_id": context["mission_id"], "status": "pending_approval", "approval_status": "pending", "scope": context["scope"], "founder_request": context["founder_request"]}


def _action_metadata(context: dict[str, Any], signature: str, state: str) -> dict[str, Any]:
    shared = {"action_context": context, "context_signature": signature}
    if state == "change_set_ready":
        buttons = [
            _button("Review Proposed Changes", "review_changes", shared),
            {"label": "Authorize Engineering Execution", "action_type": "show_section", "target": "executions", "payload": {}},
        ]
        recommended = "Review the prepared code changes and use the existing engineering execution approval gate."
    elif state == "change_set_blocked":
        buttons = [
            _button("Retry Change Set Generation", "retry_change_set", shared),
            _button("Review Validation Errors", "review_validation_errors", shared, primary=False),
            _button("Review Mission Scope", "review_scope", shared, primary=False),
        ]
        recommended = "Review the remaining structural errors or retry change-set generation. No additional approval is required."
    elif state == "approved":
        buttons = [_button("Continue to Planning", "continue_planning", shared)]
        recommended = "Continue the approved mission from its next incomplete safe stage."
    else:
        buttons = [
            _button("Review Mission Scope", "review_scope", shared, primary=False),
            _button("Approve Mission", "approve_mission", shared),
            _button("Save Mission", "save_mission", shared, primary=False),
        ]
        recommended = "Review and approve the focused mission scope."
    return {"intent_type": "create_new_mission", "recommended_action": recommended, "founder_approval_required": state not in {"approved", "change_set_blocked", "change_set_ready"}, "action_buttons": buttons}


def _button(label: str, action: str, shared: dict[str, Any], *, primary: bool = True) -> dict[str, Any]:
    return {"label": label, "action_type": "post" if primary else "post_secondary", "target": ACTION_ENDPOINT, "payload": {"action": action, **shared}}


def _scope_response(context: dict[str, Any], signature: str, state: dict[str, Any]) -> dict[str, Any]:
    scope = context["scope"]
    text = "\n".join([
        f"Mission scope: {context['title']}", "", f"Objective: {scope['objective']}", "", "Acceptance criteria:", *[f"- {item}" for item in scope["acceptance_criteria"]], "", "In scope:", *[f"- {item}" for item in scope["in_scope"]], "", "Out of scope:", *[f"- {item}" for item in scope["out_of_scope"]], "", "Governance boundaries:", *[f"- {item}" for item in scope["governance_boundaries"]], "", f"Next: {scope['expected_next_action']}",
    ])
    action_state = "change_set_blocked" if state.get("status") == "blocked" and state.get("failed_stage") == "executable_change_set" else "approved" if state.get("approval_status") == "approved" else "pending_approval"
    return {"status": "mission-scope-ready", "mission_id": context["mission_id"], "scope": scope, "board_room_response": text, "action_metadata": _action_metadata(context, signature, action_state), "governance": _governance()}


def _saved_response(context: dict[str, Any], signature: str, state: dict[str, Any]) -> dict[str, Any]:
    return {"status": "mission-proposal-saved", "mission_id": context["mission_id"], "board_room_response": f"Mission proposal saved as {context['mission_id']}. It is still awaiting scope approval; no planning or execution has started.", "action_metadata": _action_metadata(context, signature, "pending_approval"), "governance": _governance()}


def _workflow_response(context: dict[str, Any], signature: str, state: dict[str, Any]) -> dict[str, Any]:
    workflow = state.get("workflow") if isinstance(state.get("workflow"), dict) else {}
    change_set = state.get("change_set") if isinstance(state.get("change_set"), dict) else {}
    ready = change_set.get("change_set_status") == "change_set_ready"
    plan = workflow.get("planning_result") if isinstance(workflow.get("planning_result"), dict) else {}
    architecture = workflow.get("architecture_review") if isinstance(workflow.get("architecture_review"), dict) else {}
    handoff = workflow.get("engineering_handoff") if isinstance(workflow.get("engineering_handoff"), dict) else {}
    files = [str(item.get("path")) for item in change_set.get("files") or [] if isinstance(item, dict) and item.get("path")]
    validation = (change_set.get("validation") or {}).get("commands") or (handoff.get("validation_plan") or [])
    risks = change_set.get("risks") or (plan.get("plan") or {}).get("risks") or []
    blocked = state.get("status") == "blocked"
    next_action = "Authorize engineering execution using the existing exact GitHub execution approval contract." if ready else str(change_set.get("next_action") or "Retry executable change-set generation after reviewing validation errors.")
    lines = [
        f"Mission: {context['mission_id']}",
        f"Scope: {'approved' if state.get('approval_status') == 'approved' else 'pending approval'}",
        f"Planning: {_stage_status(workflow, 'planning_status')}",
        f"Architecture review: {_stage_status(workflow, 'architecture_review_status')}",
        f"Engineering handoff: {_stage_status(workflow, 'engineering_handoff_status')}",
        f"Executable change set: {'ready' if ready else 'blocked'}",
    ]
    if files:
        lines.extend(["", "Proposed files:", *[f"- {item}" for item in files]])
    if validation:
        lines.extend(["", "Validation plan:", *[f"- {item}" for item in validation]])
    if risks:
        lines.extend(["", "Risks:", *[f"- {item}" for item in risks]])
    if ready:
        lines.extend(["", "Code changes prepared — awaiting engineering execution approval.", f"Next approval required: {next_action}"])
    else:
        remaining = (change_set.get("validation") or {}).get("remaining_failed_checks") or []
        lines.extend(["", f"Blocked at {state.get('failed_stage') or 'safe preparation'}: {state.get('blocked_reason') or 'Review the failure evidence.'}"])
        if remaining:
            lines.extend(["", "Remaining validation issues:", *[f"- {_validation_issue(item)}" for item in remaining]])
        lines.extend(["", "No repository action was taken.", f"Next action: {next_action}", "Approval required: none"])
    action_state = "change_set_ready" if ready else "change_set_blocked" if blocked and state.get("failed_stage") == "executable_change_set" else "approved" if state.get("approval_status") == "approved" else "pending_approval"
    return {"status": state.get("status"), "mission_id": context["mission_id"], "board_room_response": "\n".join(lines), "action_metadata": _action_metadata(context, signature, action_state), "planning_result": plan, "architecture_review": architecture, "engineering_handoff": handoff, "executable_change_set": change_set, "failed_stage": state.get("failed_stage"), "blocked_stage": state.get("failed_stage"), "blocked_reason": state.get("blocked_reason"), "next_action": next_action, "approval_required": "engineering_execution" if ready else "none", "safe_retry_action": "retry_change_set" if action_state == "change_set_blocked" else None, "governance": _governance()}


def _validation_errors_response(context: dict[str, Any], signature: str, state: dict[str, Any]) -> dict[str, Any]:
    change_set = state.get("change_set") if isinstance(state.get("change_set"), dict) else {}
    remaining = (change_set.get("validation") or {}).get("remaining_failed_checks") or []
    if not remaining:
        return _failure(context["mission_id"], "executable_change_set", "No structural validation errors are available for review.", action_metadata=_action_metadata(context, signature, "change_set_blocked"))
    text = "\n".join([
        f"Validation issues for {context['mission_id']}:",
        *[f"- {_validation_issue(item)}" for item in remaining],
        "",
        "Candidate contents remain hidden. No repository action was taken.",
        "Next action: Retry executable change-set generation after reviewing these errors.",
        "Approval required: none",
    ])
    return {"status": "validation-errors-ready", "mission_id": context["mission_id"], "board_room_response": text, "validation_errors": remaining, "action_metadata": _action_metadata(context, signature, "change_set_blocked"), "approval_required": "none", "governance": _governance()}


def _validation_issue(item: dict[str, Any]) -> str:
    target = str(item.get("path") or "change-set schema")
    return f"{target}: {item.get('name') or 'validation'} — {item.get('reason') or 'Validation failed.'}"


def _changes_response(context: dict[str, Any], signature: str, state: dict[str, Any]) -> dict[str, Any]:
    change_set = state.get("change_set") if isinstance(state.get("change_set"), dict) else {}
    if change_set.get("change_set_status") != "change_set_ready":
        return _failure(context["mission_id"], "executable_change_set", "No prepared change set is available yet.", action_metadata=_action_metadata(context, signature, "approved"))
    files = change_set.get("files") or []
    text = "\n".join([f"Prepared changes for {context['mission_id']}:", *[f"- {item.get('path')}: {item.get('rationale') or item.get('operation')}" for item in files], "", "These files have not been written. Engineering execution still requires its exact approval phrase."])
    return {"status": "proposed-changes-ready", "mission_id": context["mission_id"], "board_room_response": text, "action_metadata": _action_metadata(context, signature, "change_set_ready"), "governance": _governance()}


def _failure(mission_id: str | None, stage: str, reason: str, *, action_metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"status": "blocked", "mission_id": mission_id, "failed_stage": stage, "blocked_reason": reason, "safe_retry_action": "Return to the Board Room and retry the safe action.", "board_room_response": reason, "action_metadata": action_metadata or {"action_buttons": []}, "governance": _governance()}


def _persist_state(state: dict[str, Any]) -> None:
    create_platform_tables()
    result = {"workflow_run_id": state["action_context_id"], "workflow_name": "Board Room Governed Mission Preparation", "status": state.get("status"), "plan_status": (state.get("workflow") or {}).get("planning_status"), "simulation": False, "step_count": 1, "completed_step_count": 1, "blocked_step_count": 1 if state.get("status") == "blocked" else 0, "failed_step_count": 0, "step_runs": [{"step_run_id": f"{state['action_context_id']}-STATE", "step_id": "mission_state", "title": "Mission lifecycle evidence", "status": "completed", "output": {"bridge_result": {"handler_result": state}}, "error": {}, "workflow_context": {"mission_id": state.get("mission_id")}}]}
    db = PlatformSessionLocal()
    try:
        persist_workflow_result(db, result=result)
    finally:
        db.close()


def _load_state(action_context_id: str) -> dict[str, Any] | None:
    create_platform_tables()
    db = PlatformSessionLocal()
    try:
        detail = get_workflow_run_detail(db, workflow_run_id=action_context_id)
    finally:
        db.close()
    for step in detail.get("steps") or []:
        if step.get("step_id") == "mission_state" and isinstance(step.get("handler_result"), dict):
            return step["handler_result"]
    return None


def _sign_context(context: dict[str, Any]) -> str:
    body = json.dumps(context, sort_keys=True, separators=(",", ":"))
    secret = os.getenv("MISSION_CONTROL_SESSION_SECRET") or "development-session-secret-change-me"
    return hmac.new(secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()


def _valid_context(context: dict[str, Any], signature: str) -> bool:
    required = {"action_context_id", "proposal_id", "request_id", "mission_id", "founder_request", "scope", "governance_version"}
    return required.issubset(context) and context.get("governance_version") == "MC-ACTION-01" and hmac.compare_digest(_sign_context(context), signature)


def _stage_status(workflow: dict[str, Any], key: str) -> str:
    value = str(workflow.get(key) or "blocked")
    if value == "reused":
        return "prepared" if key == "engineering_handoff_status" else "completed"
    return value


def _governance() -> dict[str, bool]:
    return {"mission_scope_approval": True, "repository_mutation": False, "branch_creation": False, "commit": False, "push": False, "pull_request_creation": False, "merge": False, "deployment": False, "rollback": False, "traffic_shift": False}


def _title(request: str) -> str:
    words = request.split()
    return " ".join(words[:12]).rstrip(".") or "Focused implementation mission"
