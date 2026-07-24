from __future__ import annotations

from app.platform.events.agent_task_lifecycle_publisher import publish_agent_task_lifecycle

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import IntegrityError

from app.platform.auth.service import require_founder
from app.platform.engineering.change_set_service import generate_executable_change_set
from app.platform.execution.orchestrator import launch_approved_mission_workflow
from app.platform.execution.service import record_execution_mission_evidence
from app.platform.operating_console.delivery_contract import (
    add_existing_artifact,
    advance_contract,
    build_product_definition,
    build_ux_specification,
    create_delivery_contract,
    public_delivery_summary,
)
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables, verify_platform_persistence_connection
from app.platform.persistence.models import PlatformAgentTask, PlatformWorkflowRun
from app.platform.persistence.readiness import inspect_platform_persistence_readiness
from app.platform.services.workflow_run_persistence_service import get_workflow_run_detail, persist_workflow_result


TASK_TYPE = "approved_mission_stage"
TERMINAL_STATES = {"change_set_ready", "blocked", "failed"}
_RUN_CREDENTIALS: dict[str, str] = {}
logger = logging.getLogger(__name__)


def accept_mission_run(*, context: dict[str, Any], signature: str, approval: dict[str, Any], token: str) -> dict[str, Any]:
    mission_id = str(context["mission_id"])
    run_id = _run_id(mission_id, str(context["action_context_id"]))
    readiness = inspect_platform_persistence_readiness()
    if readiness["durable_runtime_available"]:
        try:
            existing = load_mission_run(run_id, ensure_tables=False)
        except Exception:
            existing = {"found": False}
        if existing.get("found"):
            _remember_credential(run_id, token)
            _activate_if_non_terminal(existing)
            _log("mission_run.reused", mission_id=mission_id, workflow_run_id=run_id)
            return mission_run_envelope(existing, reused=True)
    if readiness["durable_runtime_available"]:
        readiness = verify_platform_persistence_connection(readiness)
    if not readiness["durable_runtime_available"]:
        return _persistence_blocked(mission_id, run_id, readiness)
    _remember_credential(run_id, token)
    existing = load_mission_run(run_id)
    if existing.get("found"):
        _activate_if_non_terminal(existing)
        return mission_run_envelope(existing, reused=True)
    now = _now()
    decision_state = _load_founder_decision_state(context)
    state = {
        "workflow_run_id": run_id,
        "mission_id": mission_id,
        "action_context_id": context["action_context_id"],
        "context_signature": signature,
        "context": context,
        "approval": approval,
        "status": "accepted",
        "current_stage": "accepted",
        "created_at": now,
        "updated_at": now,
        "steps": [_step("accepted", "completed", "Mission accepted and durable work queued.")],
        "delivery_contract": create_delivery_contract(
            context=context,
            workflow_run_id=run_id,
            decision_state=decision_state,
        ),
        "error": None,
    }
    _persist(state)
    _enqueue(run_id, mission_id, "prepare")
    _activate_canonical_worker()
    _log("mission_run.accepted", mission_id=mission_id, workflow_run_id=run_id)
    return mission_run_envelope(state, reused=False)


def get_mission_run_status(payload: dict[str, Any]) -> dict[str, Any]:
    authorized = require_founder(payload)
    if not authorized.get("authorized"):
        return _error("Founder authentication is required.")
    run_id = str(payload.get("workflow_run_id") or "").strip()
    _remember_credential(run_id, str(payload.get("token") or ""))
    state = load_mission_run(run_id)
    if not state.get("found"):
        return _error("The mission run could not be found.", run_id)
    resumed = _resume_authorization_if_possible(state)
    _activate_if_non_terminal(state)
    _log("board_room.mission_resumed", mission_id=str(state.get("mission_id") or "unknown"), workflow_run_id=run_id, resumed=resumed)
    return mission_run_envelope(state, reused=True)


def build_mission_execution_summary() -> dict[str, Any]:
    state = find_latest_mission_run()
    if not state.get("found"):
        return {
            "status": "no-active-durable-mission",
            "runtime_classification": "durable_platform_workflow",
            "durable_runtime_created": False,
            "active_mission": None,
            "message": "Select or create a Board Room mission before creating an execution mission.",
        }
    envelope = mission_run_envelope(state, reused=True)
    return {**envelope, "active_mission": _active_mission(state)}


def continue_mission_run(payload: dict[str, Any]) -> dict[str, Any]:
    authorized = require_founder(payload)
    if not authorized.get("authorized"):
        return _error("Founder authentication is required.")
    run_id = str(payload.get("workflow_run_id") or "").strip()
    mission_id = str(payload.get("mission_id") or "").strip()
    if not run_id or not mission_id:
        return _error("Load a durable mission before continuing it.", run_id or None)
    state = load_mission_run(run_id)
    if not state.get("found") or state.get("mission_id") != mission_id:
        return _error("The selected durable mission could not be found.", run_id)
    if not _advance_allowed(state):
        return _transition_error(state)
    _remember_credential(run_id, str(payload.get("token") or ""))
    resumed = _resume_authorization_if_possible(state)
    if str(state.get("current_stage") or "") == "blocked" and not resumed:
        return _transition_error(state, "This blocked mission cannot be resumed automatically. Review its blocker before continuing.")
    _activate_if_non_terminal(state)
    current = load_mission_run(run_id) if resumed else state
    return mission_run_envelope(current, reused=True)


def execute_mission_task(task: dict[str, Any]) -> dict[str, Any]:
    payload = task.get("input_payload") if isinstance(task.get("input_payload"), dict) else {}
    run_id = str(payload.get("workflow_run_id") or "")
    state = load_mission_run(run_id)
    if not state.get("found"):
        return {"success": False, "error": "mission_run_not_found"}
    token = _RUN_CREDENTIALS.get(run_id)
    if not token:
        _block(state, "authorization_resume_required", "Founder session must be restored before durable work can resume.", retryable=True)
        _log("mission_task.blocked", mission_id=str(state.get("mission_id") or "unknown"), workflow_run_id=run_id, classification="authorization_resume_required")
        return {"success": False, "error": "authorization_resume_required"}
    try:
        _log("mission_task.stage_started", mission_id=str(state.get("mission_id") or "unknown"), workflow_run_id=run_id, stage=str(payload.get("stage") or "unknown"))
        if payload.get("stage") == "prepare":
            result = _execute_preparation(state, token)
            _log_stage_result(result, state, run_id, "prepare")
            return result
        if payload.get("stage") == "change_set":
            result = _execute_change_set(state)
            _log_stage_result(result, state, run_id, "change_set")
            return result
        raise ValueError("unsupported mission stage")
    except Exception as exc:
        _block(state, _classify(exc), f"Mission stage failed safely: {type(exc).__name__}.", retryable=True)
        _log("mission_task.failed", mission_id=str(state.get("mission_id") or "unknown"), workflow_run_id=run_id, classification=str(state["error"]["classification"]))
        return {"success": False, "error": state["error"]["classification"]}


def _execute_preparation(state: dict[str, Any], token: str) -> dict[str, Any]:
    context = state["context"]
    observer = _progress_observer(state)
    workflow = launch_approved_mission_workflow(
        {
            "token": token,
            "mission_id": state["mission_id"],
            "approval": state["approval"],
            "founder_request": context["founder_request"],
            "title": context["title"],
            "progress_observer": observer,
        }
    )
    state["workflow"] = workflow
    if workflow.get("workflow_status") != "engineering-handoff-prepared":
        _block(state, str(workflow.get("current_stage") or "preparation_failure"), str(workflow.get("blocked_reason") or "Mission preparation did not complete."), retryable=True)
        return {"success": False, "error": state["error"]["classification"]}
    architecture = workflow.get("architecture_review") or {}
    if (architecture.get("architecture_decision") or {}).get("status") != "validated":
        _block(state, "architecture_validation_failure", "Architecture decision was not validated.", retryable=False)
        return {"success": False, "error": "architecture_validation_failure"}
    planning = workflow.get("planning_result") if isinstance(workflow.get("planning_result"), dict) else {}
    product_definition = build_product_definition(state=state, planning=planning)
    ux_specification = build_ux_specification(
        state=state,
        product_definition=product_definition,
    )
    architecture_artifact = add_existing_artifact(
        state=state,
        artifact_type="architecture_decision",
        authority="architecture_agent",
        content=architecture.get("architecture_decision") or architecture,
        source_references=[
            product_definition["artifact_id"],
            ux_specification["artifact_id"],
        ],
        evidence_references=[
            str((architecture.get("architecture_decision") or {}).get("decision_id") or "")
        ],
    )
    handoff = workflow.get("engineering_handoff") if isinstance(workflow.get("engineering_handoff"), dict) else {}
    add_existing_artifact(
        state=state,
        artifact_type="engineering_plan",
        authority="engineering_manager",
        content=handoff,
        source_references=[
            product_definition["artifact_id"],
            architecture_artifact["artifact_id"],
        ],
        evidence_references=[str(handoff.get("breakdown_id") or "")],
    )
    advance_contract(state["delivery_contract"], "engineering_plan")
    _persist(state)
    _enqueue(state["workflow_run_id"], state["mission_id"], "change_set")
    return {"success": True, "stage": "engineering_handoff_completed"}


def _execute_change_set(state: dict[str, Any]) -> dict[str, Any]:
    context = state["context"]
    result = generate_executable_change_set(
        {"mission_id": state["mission_id"], "provider": context.get("provider"), "model": context.get("model"), "progress_observer": _progress_observer(state)}
    )
    record_execution_mission_evidence(state["mission_id"], "executable_change_set", result)
    state["change_set"] = result
    if result.get("change_set_status") != "change_set_ready":
        _block(state, "change_set_validation_failure", str(result.get("blocked_reason") or "Proposed changes did not pass validation."), retryable=True)
        return {"success": False, "error": "change_set_validation_failure"}
    change_set_artifact = add_existing_artifact(
        state=state,
        artifact_type="change_set",
        authority="engineering_change_set_service",
        content=result,
        source_references=[
            item["artifact_id"]
            for item in state["delivery_contract"].get("artifacts") or []
            if item.get("artifact_type") == "engineering_plan"
        ],
        evidence_references=[
            str(result.get("change_set_id") or ""),
        ],
    )
    validation = result.get("validation") if isinstance(result.get("validation"), dict) else {}
    state["delivery_contract"].setdefault("validation_evidence_references", []).extend(
        [
            str(value)
            for value in (
                validation.get("evidence_id"),
                change_set_artifact["artifact_id"],
            )
            if value
        ]
    )
    advance_contract(
        state["delivery_contract"],
        "repository_approval",
        next_governed_action={
            "capability": "github.repository_mutation",
            "authority": "governance_authorization",
            "approval_required": True,
        },
    )
    _advance(state, "change_set_ready", "Proposed changes passed structural validation and are ready for founder review.")
    _RUN_CREDENTIALS.pop(state["workflow_run_id"], None)
    return {"success": True, "stage": "change_set_ready"}


def _activate_canonical_worker() -> None:
    from app.platform.agents.worker import ensure_agent_worker_running

    ensure_agent_worker_running(task_type=TASK_TYPE)


def _activate_if_non_terminal(state: dict[str, Any]) -> None:
    if str(state.get("current_stage") or "accepted") not in TERMINAL_STATES:
        _activate_canonical_worker()


def load_mission_run(run_id: str, *, ensure_tables: bool = True) -> dict[str, Any]:
    if not run_id:
        return {"found": False}
    if ensure_tables:
        create_platform_tables()
    db = PlatformSessionLocal()
    try:
        detail = get_workflow_run_detail(db, workflow_run_id=run_id)
    finally:
        db.close()
    for item in detail.get("steps") or []:
        if item.get("step_id") == "mission_run_state" and isinstance(item.get("handler_result"), dict):
            return {**item["handler_result"], "found": True}
    return {"found": False, "workflow_run_id": run_id}


def mission_run_envelope(state: dict[str, Any], *, reused: bool) -> dict[str, Any]:
    stage = str(state.get("current_stage") or "accepted")
    context = state.get("context") if isinstance(state.get("context"), dict) else {}
    next_action = _next_governed_action(state)
    return {
        "ok": stage not in {"blocked", "failed"},
        "status": stage if stage in TERMINAL_STATES else "accepted" if stage == "accepted" else "in_progress",
        "mission_id": state.get("mission_id"),
        "workflow_run_id": state.get("workflow_run_id"),
        "action_context_id": state.get("action_context_id"),
        "context_signature": state.get("context_signature"),
        "originating_mission_id": context.get("originating_mission_id") or context.get("original_mission_id") or state.get("mission_id"),
        "original_mission_id": context.get("original_mission_id") or context.get("originating_mission_id") or state.get("mission_id"),
        "founder_request": context.get("founder_request"),
        "title": context.get("title"),
        "provider": context.get("provider"),
        "model": context.get("model"),
        "approval": state.get("approval"),
        "runtime_classification": "durable_platform_workflow",
        "durable_runtime_created": True,
        "message": _message(stage),
        "advance_allowed": _advance_allowed(state),
        "next_governed_action": next_action,
        "progress": {"current_stage": stage, "terminal": stage in TERMINAL_STATES, "steps": state.get("steps") or []},
        "error": state.get("error"),
        "reused": reused,
        "worker_dispatch": {"required": stage not in TERMINAL_STATES, "configured": True, "transport": "PlatformAgentTask + Agent Worker"},
        "task_status": _task_snapshot(str(state.get("workflow_run_id") or "")),
        "delivery": public_delivery_summary(state.get("delivery_contract")),
        "governance": {key: False for key in ("repository_mutation", "branch_creation", "commit", "push", "pull_request_creation", "merge", "deployment", "rollback", "traffic_shift")},
    }


def _active_mission(state: dict[str, Any]) -> dict[str, Any]:
    envelope = mission_run_envelope(state, reused=True)
    steps = state.get("steps") or []
    return {
        **{key: envelope.get(key) for key in ("mission_id", "workflow_run_id", "action_context_id", "originating_mission_id", "original_mission_id", "founder_request", "title", "status", "runtime_classification", "durable_runtime_created", "task_status", "advance_allowed", "next_governed_action")},
        "current_stage": (envelope.get("progress") or {}).get("current_stage"),
        "progress_percentage": None,
        "approval_required": True,
        "stages": [{"name": item.get("specialist_stage"), "label": str(item.get("specialist_stage") or "Unknown").replace("_", " ").title(), "completed": item.get("status") == "completed", "status": item.get("status")} for item in steps],
        "next_recommended_action": (envelope.get("next_governed_action") or {}).get("description") or envelope.get("message"),
        "blocker": (envelope.get("error") or {}).get("technical_summary"),
        "delivery": envelope.get("delivery"),
    }


def _load_founder_decision_state(context: dict[str, Any]) -> dict[str, Any] | None:
    conversation_id = str(context.get("conversation_id") or "").strip()
    if not conversation_id:
        return None
    from app.platform.founder_decision.service import load_decision_experience

    return load_decision_experience(conversation_id)


def _task_snapshot(run_id: str) -> dict[str, Any]:
    if not run_id:
        return {"count": 0, "current": None}
    db = PlatformSessionLocal()
    try:
        try:
            tasks = db.query(PlatformAgentTask).filter(PlatformAgentTask.parent_task_id == run_id, PlatformAgentTask.task_type == TASK_TYPE).order_by(PlatformAgentTask.updated_at.desc()).all()
        except Exception:
            return {"count": None, "current": None, "status": "unknown"}
        current = tasks[0] if tasks else None
        return {
            "count": len(tasks),
            "current": None if current is None else {"task_id": current.task_id, "status": current.status, "attempts": current.attempts, "max_attempts": current.max_attempts, "assigned_agent": current.assigned_agent},
        }
    finally:
        db.close()


def _enqueue(run_id: str, mission_id: str, stage: str) -> None:
    create_platform_tables()
    task_id = f"TASK-{hashlib.sha256(f'{run_id}:{stage}'.encode()).hexdigest()[:20].upper()}"
    db = PlatformSessionLocal()
    try:
        if db.query(PlatformAgentTask).filter(PlatformAgentTask.task_id == task_id).first():
            return
        task = PlatformAgentTask(
            task_id=task_id,
            title=f"Continue {mission_id}: {stage}",
            status="queued",
            priority="high",
            risk_level="low",
            task_type=TASK_TYPE,
            requested_by="founder_approved_mission",
            input_payload_json=json.dumps(
                {
                    "workflow_run_id": run_id,
                    "mission_id": mission_id,
                    "stage": stage,
                }
            ),
            result_payload_json="{}",
            approval_required=False,
            parent_task_id=run_id,
            max_attempts=3,
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        publish_agent_task_lifecycle(
            {
                "task_id": task.task_id,
                "task_type": task.task_type,
                "parent_task_id": task.parent_task_id,
                "assigned_agent": task.assigned_agent,
                "attempts": task.attempts,
                "max_attempts": task.max_attempts,
                "input_payload": {
                    "workflow_run_id": run_id,
                    "mission_id": mission_id,
                    "stage": stage,
                },
            },
            lifecycle_status="queued",
            assigned_agent=task.assigned_agent,
        )

        _log(
            "agent_task.enqueued",
            mission_id=mission_id,
            workflow_run_id=run_id,
            task_id=task_id,
            stage=stage,
        )
    except IntegrityError:
        db.rollback()
    finally:
        db.close()


def _persist(state: dict[str, Any]) -> None:
    steps = state.get("steps") or []
    result = {"workflow_run_id": state["workflow_run_id"], "workflow_name": "Durable Board Room Mission Run", "status": state.get("status"), "plan_status": state.get("current_stage"), "simulation": False, "step_count": len(steps), "completed_step_count": sum(item["status"] == "completed" for item in steps), "blocked_step_count": sum(item["status"] == "blocked" for item in steps), "failed_step_count": 0, "metadata": {"mission_id": state.get("mission_id"), "runtime": "MC-RUNTIME-01A"}, "step_runs": [{"step_run_id": f"{state['workflow_run_id']}-STATE", "step_id": "mission_run_state", "title": "Durable mission work status", "status": state.get("status"), "output": {"bridge_result": {"handler_result": state}}, "error": state.get("error") or {}}]}
    db = PlatformSessionLocal()
    try:
        persist_workflow_result(db, result=result)
    finally:
        db.close()


def _advance(state: dict[str, Any], stage: str, summary: str) -> None:
    state.update({"status": stage, "current_stage": stage, "updated_at": _now(), "error": None})
    state.setdefault("steps", []).append(_step(stage, "completed" if stage in {"engineering_handoff_completed", "change_set_ready"} else "running", summary))
    _persist(state)
    if stage in TERMINAL_STATES:
        _log("mission_run.terminal", mission_id=str(state.get("mission_id") or "unknown"), workflow_run_id=str(state.get("workflow_run_id") or "unknown"), stage=stage)


def _progress_observer(state: dict[str, Any]):
    def observe(*, stage: str, status: str, summary: str) -> None:
        current = f"{stage}_{status}"
        state.update({"status": current, "current_stage": current, "updated_at": _now(), "error": None})
        state.setdefault("steps", []).append(_step(stage, status, summary))
        _persist(state)

    return observe


def _block(state: dict[str, Any], classification: str, summary: str, *, retryable: bool) -> None:
    state.update({"status": "blocked", "current_stage": "blocked", "updated_at": _now(), "error": {"classification": classification, "retryable": retryable, "technical_summary": summary[:500]}})
    state.setdefault("steps", []).append(_step(classification, "blocked", summary))
    _persist(state)
    _log("mission_run.blocked", mission_id=str(state.get("mission_id") or "unknown"), workflow_run_id=str(state.get("workflow_run_id") or "unknown"), classification=classification)


def find_latest_mission_run(mission_id: str | None = None) -> dict[str, Any]:
    db = PlatformSessionLocal()
    try:
        query = db.query(PlatformWorkflowRun).filter(PlatformWorkflowRun.workflow_name == "Durable Board Room Mission Run")
        rows = query.order_by(PlatformWorkflowRun.updated_at.desc()).limit(50).all()
        for row in rows:
            state = load_mission_run(row.workflow_run_id, ensure_tables=False)
            if state.get("found") and (not mission_id or state.get("mission_id") == mission_id):
                return state
    finally:
        db.close()
    return {"found": False, "mission_id": mission_id}


def _resume_authorization_if_possible(state: dict[str, Any]) -> bool:
    error = state.get("error") if isinstance(state.get("error"), dict) else {}
    if error.get("classification") != "authorization_resume_required" or not _RUN_CREDENTIALS.get(str(state.get("workflow_run_id") or "")):
        return False
    db = PlatformSessionLocal()
    try:
        task = db.query(PlatformAgentTask).filter(
            PlatformAgentTask.parent_task_id == state["workflow_run_id"],
            PlatformAgentTask.task_type == TASK_TYPE,
            PlatformAgentTask.status == "failed",
            PlatformAgentTask.error_message == "authorization_resume_required",
            PlatformAgentTask.attempts < PlatformAgentTask.max_attempts,
        ).order_by(PlatformAgentTask.updated_at.desc()).first()
        if not task:
            return False
        task.status = "queued"
        task.assigned_agent = None
        task.claimed_at = None
        task.failed_at = None
        task.error_message = None
        task.result_payload_json = "{}"
        db.commit()
    finally:
        db.close()
    state.update({"status": "accepted", "current_stage": "authorization_resumed", "updated_at": _now(), "error": None})
    state.setdefault("steps", []).append(_step("authorization_resumed", "completed", "Authenticated founder session restored safe mission preparation."))
    _persist(state)
    return True


def _log(event: str, **fields: object) -> None:
    detail = " ".join(f"{key}={str(value)[:120]}" for key, value in sorted(fields.items()))
    logger.info("%s %s", event, detail)


def _log_stage_result(result: dict[str, Any], state: dict[str, Any], run_id: str, stage: str) -> None:
    event = "mission_task.stage_completed" if result.get("success") else "mission_task.blocked"
    _log(event, mission_id=str(state.get("mission_id") or "unknown"), workflow_run_id=run_id, stage=stage, classification=str(result.get("error") or "none"))


def _step(stage: str, status: str, summary: str) -> dict[str, Any]:
    now = _now()
    return {"specialist_stage": stage, "status": status, "started_at": now, "completed_at": now if status != "running" else None, "result_summary": summary[:500]}


def _remember_credential(run_id: str, token: str) -> None:
    if run_id and token:
        _RUN_CREDENTIALS[run_id] = token


def _run_id(mission_id: str, action_context_id: str) -> str:
    return f"MISSION-RUN-{hashlib.sha256(f'{mission_id}:{action_context_id}'.encode()).hexdigest()[:16].upper()}"


def _message(stage: str) -> str:
    return {
        "accepted": "Mission accepted. Durable preparation has started.",
        "planning_running": "Planning Agent is preparing the mission-specific plan.",
        "capability_intelligence_running": "Capability Intelligence is identifying reusable platform capabilities.",
        "repository_intelligence_running": "Repository Intelligence is inspecting approved targets.",
        "architecture_agent_running": "Architecture Agent is evaluating reuse and integration.",
        "architecture_validation_running": "Architecture Validator is checking the decision evidence.",
        "engineering_manager_running": "Engineering Manager is preparing the handoff.",
        "change_set_generation_running": "Change-Set Generator is preparing proposed changes.",
        "change_set_validation_running": "Validator is checking the proposed changes.",
        "change_set_repair_running": "One bounded repair attempt is in progress.",
        "change_set_ready": "Proposed changes are ready for founder review.",
        "blocked": "Mission preparation is blocked. Review the preserved work status.",
    }.get(stage, "Mission Control is continuing the approved mission.")


def _advance_allowed(state: dict[str, Any]) -> bool:
    stage = str(state.get("current_stage") or "accepted")
    error = state.get("error") if isinstance(state.get("error"), dict) else {}
    return stage not in TERMINAL_STATES or (stage == "blocked" and error.get("classification") == "authorization_resume_required")


def _next_governed_action(state: dict[str, Any]) -> dict[str, Any]:
    stage = str(state.get("current_stage") or "accepted")
    error = state.get("error") if isinstance(state.get("error"), dict) else {}
    if stage == "change_set_ready":
        return {
            "action_type": "show_section", "target": "executions",
            "label": "Review & Authorize GitHub Execution",
            "description": "Review the prepared change set and use the separate founder-approved GitHub execution gate.",
        }
    if stage in {"pull_request_open", "pr_review", "awaiting_merge_approval"}:
        return {
            "action_type": "show_section", "target": "executions", "label": "Open PR Lifecycle",
            "description": "Review pull request checks and merge readiness before any founder-approved merge.",
        }
    if stage == "blocked" and error.get("classification") == "authorization_resume_required":
        return {
            "action_type": "advance", "target": "/mission-control/execution/advance",
            "label": "Resume Mission", "description": "Restore founder authorization and resume the preserved durable task.",
        }
    if stage in {"blocked", "failed"}:
        return {
            "action_type": "none", "target": None, "label": "Review Mission Blocker",
            "description": "Review the preserved failure details before choosing a safe recovery action.",
        }
    return {
        "action_type": "advance", "target": "/mission-control/execution/advance",
        "label": "Continue Mission", "description": "Continue the next incomplete stage of the durable mission.",
    }


def _transition_error(state: dict[str, Any], message: str | None = None) -> dict[str, Any]:
    stage = str(state.get("current_stage") or "unknown")
    action = _next_governed_action(state)
    detail = message or "The mission cannot advance from {}. {}".format(stage.replace("_", " "), action["description"])
    return {
        **mission_run_envelope(state, reused=True), "ok": False, "message": detail,
        "error": {"classification": "invalid_stage_transition", "retryable": False, "technical_summary": detail},
    }


def _classify(exc: Exception) -> str:
    text = f"{type(exc).__name__} {exc}".lower()
    if "timeout" in text or "deadline" in text:
        return "workflow_timeout"
    if "json" in text or "decode" in text:
        return "provider_non_json_response"
    return "unknown_runtime_failure"


def _error(message: str, run_id: str | None = None) -> dict[str, Any]:
    return {"ok": False, "status": "failed", "workflow_run_id": run_id, "message": message, "error": {"classification": "authorization_or_lookup", "retryable": True, "technical_summary": message}}


def _persistence_blocked(mission_id: str, run_id: str, readiness: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": False,
        "status": "blocked",
        "mission_id": mission_id,
        "workflow_run_id": run_id,
        "message": "Shared platform persistence is not commissioned. Durable mission execution was not started.",
        "progress": {"current_stage": "persistence_readiness", "terminal": True, "steps": []},
        "error": {"classification": "platform_persistence_unavailable", "retryable": True, "technical_summary": "; ".join(readiness.get("reasons") or [])[:500]},
        "platform_persistence": readiness,
        "reused": False,
        "worker_dispatch": {"required": False, "configured": False, "transport": None},
        "governance": {key: False for key in ("repository_mutation", "branch_creation", "commit", "push", "pull_request_creation", "merge", "deployment", "rollback", "traffic_shift")},
    }


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
