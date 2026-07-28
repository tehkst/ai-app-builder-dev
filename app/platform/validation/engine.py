from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from importlib import import_module
from time import monotonic
from typing import Any, Callable, Dict, List, Optional

from app.platform.auth.service import require_founder
from app.platform.persistence.database import PlatformSessionLocal
from app.platform.persistence.execution_migrations import run_execution_layer_migrations
from app.platform.persistence.models import PlatformValidationMission, PlatformValidationStep
from app.platform.validation.catalogue import capabilities_for


Executor = Callable[[str, Dict[str, Any]], Dict[str, Any]]
TERMINAL_SUCCESS = {
    "completed", "passed", "approved", "destroyed", "verified",
    "created", "recovered", "cleaned", "pull-request-created", "pr-merged",
    "deployment-succeeded", "deployment-completed", "verification-complete",
}
SECRET_KEYS = {"token", "github_token", "authorization", "approval_phrase", "founder_token"}


def execute_validation_mission(payload: Dict[str, Any], executor: Optional[Executor] = None, *, allow_test_mode: bool = False) -> Dict[str, Any]:
    validation_type = str(payload.get("validation_type") or "").strip()
    capabilities = capabilities_for(validation_type)
    if not capabilities:
        return {"status": "invalid", "error": "Unknown validation_type.", "available_types": _types()}
    mode = str(payload.get("execution_mode") or "live").strip().lower()
    if mode not in {"live", "test"}:
        return {"status": "invalid", "error": "execution_mode must be live or test."}
    if mode == "test" and not allow_test_mode:
        return {"status": "denied", "error": "Test-mode validation is available only to the internal validation harness."}
    if mode == "live" and not require_founder(payload).get("authorized"):
        return {"status": "denied", "error": "Valid founder authorization is required for live validation."}
    run_execution_layer_migrations()
    validation_id = str(payload.get("validation_mission_id") or "VALIDATION-%s" % uuid.uuid4().hex[:16].upper())
    mission_id = str(payload.get("mission_id") or validation_id)
    existing = validation_mission_status(validation_id)
    if existing.get("status") != "not-found":
        return existing
    started = _now()
    record = PlatformValidationMission(
        validation_mission_id=validation_id, mission_id=mission_id,
        validation_type=validation_type, execution_mode=mode, status="running",
        capabilities_json=json.dumps(capabilities), authorization_json=json.dumps({"founder_authorized": mode == "live"}),
        started_at=started, created_at=started, updated_at=started,
    )
    with PlatformSessionLocal() as db:
        db.add(record)
        db.commit()
    operation_inputs = payload.get("operations") if isinstance(payload.get("operations"), dict) else {}
    dispatch = executor or _dispatch
    log: List[Dict[str, Any]] = []
    shared: Dict[str, Any] = {"mission_id": mission_id}
    all_passed = True
    hard_failed = False
    trust_blocked = False
    for sequence, capability in enumerate(capabilities, 1):
        operation = dict(shared)
        operation.update(operation_inputs.get(capability) or {})
        operation.update({
            "mission_id": mission_id, "actor": str(payload.get("actor") or "mission_control"),
            "token": payload.get("token"), "execution_mode": mode,
        })
        step = _start_step(validation_id, sequence, capability, operation)
        tick = monotonic()
        try:
            outcome = dispatch(capability, operation)
            passed = _outcome_passed(outcome)
            step_trust_blocked = str(outcome.get("status") or "").lower() == "blocked_by_trust_prerequisite"
            error = None if passed else str(outcome.get("error") or outcome.get("reason") or "Capability did not complete successfully.")
        except Exception as exc:
            outcome = {"status": "failed", "error_type": type(exc).__name__}
            passed = False
            step_trust_blocked = False
            error = "Executor raised %s." % type(exc).__name__
        verification = {
            "passed": passed, "execution_mode": mode,
            "acceptance_eligible": mode == "live" and passed,
            "outcome_status": outcome.get("status"),
            "blocked_by_trust_prerequisite": step_trust_blocked,
        }
        evidence_id = _evidence_id(outcome)
        shared.update({key: value for key, value in outcome.items() if key in {"approval_id", "workspace_id", "pr_number", "pull_request_number", "release_id", "tag_name", "revision_name"} and value is not None})
        authorization = outcome.get("authorization") if isinstance(outcome.get("authorization"), dict) else {}
        _finish_step(step, verification, authorization, evidence_id, error, int((monotonic() - tick) * 1000))
        log.append({"execution_id": step.execution_id, "capability": capability, "passed": passed, "evidence_id": evidence_id})
        all_passed = all_passed and passed
        trust_blocked = trust_blocked or step_trust_blocked
        hard_failed = hard_failed or (not passed and not step_trust_blocked)
        if not passed and not step_trust_blocked and payload.get("continue_on_failure") is not True:
            break
    cleanup = _run_cleanup(payload, dispatch, shared)
    cleanup_passed = cleanup.get("status") in {"completed", "not-required"}
    if all_passed and len(log) == len(capabilities) and cleanup_passed:
        final_result = "pass"
    elif trust_blocked and not hard_failed and len(log) == len(capabilities) and cleanup_passed:
        final_result = "blocked_by_trust_prerequisite"
    else:
        final_result = "fail"
    _finish_mission(validation_id, log, cleanup, final_result, started, shared.get("workspace_id"))
    return validation_mission_status(validation_id)


def validation_mission_status(validation_mission_id: str) -> Dict[str, Any]:
    run_execution_layer_migrations()
    with PlatformSessionLocal() as db:
        mission = db.query(PlatformValidationMission).filter_by(validation_mission_id=validation_mission_id).first()
        if not mission:
            return {"status": "not-found", "validation_mission_id": validation_mission_id}
        steps = db.query(PlatformValidationStep).filter_by(validation_mission_id=validation_mission_id).order_by(PlatformValidationStep.sequence.asc()).all()
        return {
            "status": mission.status, "validation_mission_id": mission.validation_mission_id,
            "mission_id": mission.mission_id, "validation_type": mission.validation_type,
            "execution_mode": mission.execution_mode, "final_result": mission.final_result,
            "workspace_id": mission.workspace_id, "started_at": mission.started_at.isoformat(),
            "completed_at": mission.completed_at.isoformat() if mission.completed_at else None,
            "duration_ms": mission.duration_ms, "verification": _loads(mission.verification_json, {}),
            "cleanup": _loads(mission.cleanup_json, {}), "steps": [_present_step(step) for step in steps],
        }


def _dispatch(capability: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    dispatchers = (
        ("repository_", "app.platform.execution.repository_adapter", "execute_repository_action", "action"),
        ("github_", "app.platform.github_execution.adapter", "execute_github_action", "action"),
        ("release_", "app.platform.release.execution_adapter", "execute_release_action", "action"),
        ("workspace_", "app.platform.workspaces.governed_service", "execute_workspace_action", "action"),
    )
    aliases = {"create_pr": ("app.platform.github_execution.approved_executor", "execute_approved_github_execution"), "merge_pr": ("app.platform.github_execution.approved_merge", "execute_github_merge"), "deploy": ("app.platform.deployment.approved_cloud_run", "execute_cloud_run_deployment"), "production_verification": ("app.platform.deployment.production_verification", "run_production_verification")}
    if capability in aliases:
        module, function = aliases[capability]
        return getattr(import_module(module), function)(payload)
    primitive = _dispatch_validation_primitive(capability, payload)
    if primitive is not None:
        return primitive
    for prefix, module, function, field in dispatchers:
        if capability.startswith(prefix):
            request = dict(payload)
            request[field] = capability[len(prefix):]
            return getattr(import_module(module), function)(request)
    return {"status": "blocked", "error": "No canonical executor is registered for %s." % capability}


def _dispatch_validation_primitive(capability: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if capability in {"founder_request", "mission_completion"}:
        from app.platform.persistence.operational_evidence import record_operational_evidence
        evidence = record_operational_evidence(
            "platform_validation", "platform_validation_engine",
            str(payload.get("mission_id") or "unknown"), "completed",
            {"capability": capability, "execution_mode": payload.get("execution_mode")},
        )
        return {"status": "completed", "governance_evidence": evidence}
    if capability == "approval_request":
        from app.platform.governance_authorization.service import authorize_governed_action
        decision = authorize_governed_action(payload, str(payload.get("action") or "repository_fetch"), policy_context={"durable_approval_required": True})
        return {"status": "completed" if decision.get("denied") else "failed", "governance_evidence": {"evidence_id": decision.get("evidence_id")}, "authorization": decision}
    if capability == "approval_grant":
        from app.platform.governance_authorization.approvals import create_durable_approval
        result = create_durable_approval(payload)
        return dict(result, status="completed" if result.get("status") == "approved" else result.get("status"))
    if capability in {"approval_consume", "approval_replay_denial", "approval_scope_enforcement"}:
        from app.platform.governance_authorization.approvals import consume_durable_approval
        target = str(payload.get("target") or "")
        if capability == "approval_scope_enforcement":
            target = "%s-outside-scope" % target
        result = consume_durable_approval(str(payload.get("approval_id") or ""), str(payload.get("mission_id") or ""), str(payload.get("action") or ""), target)
        expected = result.get("consumed") is True if capability == "approval_consume" else result.get("consumed") is False
        return {"status": "completed" if expected else "failed", "result": result}
    if capability == "approval_expiry":
        return _validate_approval_expiry(payload)
    if capability == "sandbox_tool_execution":
        from app.platform.digital_twin.sandbox_runner import execute_sandbox_tool_execution

        return execute_sandbox_tool_execution(payload)
    if capability == "ui_ux_verification":
        from app.platform.digital_twin.ui_verification import execute_ui_ux_verification

        return execute_ui_ux_verification(payload)
    if capability.startswith("governance_"):
        return _validate_governance(capability, payload)
    if capability.startswith("workspace_"):
        return _validate_workspace_observation(capability, payload)
    if capability in {"deployment_readiness", "rollback_readiness"}:
        module_name, function_name = (
            ("app.platform.deployment.approved_cloud_run", "preview_cloud_run_deployment")
            if capability == "deployment_readiness"
            else ("app.platform.deployment.approved_rollback", "preview_cloud_run_rollback")
        )
        result = getattr(import_module(module_name), function_name)(payload)
        return dict(result, status="completed" if "blocked" not in str(result.get("status")) and "failed" not in str(result.get("status")) else "failed")
    return None


def _validate_approval_expiry(payload: Dict[str, Any]) -> Dict[str, Any]:
    from datetime import timedelta
    from sqlalchemy import update
    from app.platform.governance_authorization.approvals import consume_durable_approval
    from app.platform.persistence.models import PlatformGovernanceApproval
    approval_id = str(payload.get("approval_id") or "")
    with PlatformSessionLocal() as db:
        db.execute(update(PlatformGovernanceApproval).where(PlatformGovernanceApproval.approval_id == approval_id).values(expires_at=_now() - timedelta(seconds=1)))
        db.commit()
    result = consume_durable_approval(approval_id, str(payload.get("mission_id") or ""), str(payload.get("action") or ""), str(payload.get("target") or ""))
    return {"status": "completed" if result.get("consumed") is False else "failed", "result": result}


def _validate_governance(capability: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    from app.platform.governance_authorization.service import authorize_governed_action
    action = str(payload.get("action") or "repository_fetch")
    request = dict(payload)
    if capability == "governance_unauthorized_denial":
        request.update({"token": "", "live_execution": False, "approval_id": ""})
    decision = authorize_governed_action(request, action, policy_context={"durable_approval_required": capability != "governance_unauthorized_denial"})
    expected = decision.get("denied") is True if capability == "governance_unauthorized_denial" else decision.get("allowed") is True
    if capability == "governance_central_authority_evidence":
        expected = bool(decision.get("evidence_id"))
    return {"status": "completed" if expected else "failed", "authorization": decision, "governance_evidence": {"evidence_id": decision.get("evidence_id")}}


def _validate_workspace_observation(capability: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    from app.platform.workspaces.execution_service import acquire_workspace_lease, heartbeat_workspace, inspect_workspace
    workspace_id = str(payload.get("workspace_id") or "")
    owner = str(payload.get("owner_id") or payload.get("actor") or "mission_control")
    if capability == "workspace_heartbeat":
        result = heartbeat_workspace(workspace_id, owner)
        return {"status": "completed" if result.get("renewed") else "failed", "result": result}
    if capability == "workspace_isolation":
        result = acquire_workspace_lease(workspace_id, "%s-isolation-probe" % owner)
        return {"status": "completed" if result.get("acquired") is False else "failed", "result": result}
    if capability == "workspace_retention":
        state = inspect_workspace(workspace_id)
        return {"status": "completed" if state.get("status") != "not-found" else "failed", "result": {"workspace_id": workspace_id}}
    return None


def _start_step(validation_id: str, sequence: int, capability: str, request: Dict[str, Any]) -> PlatformValidationStep:
    step = PlatformValidationStep(
        execution_id="VALIDATION-STEP-%s" % uuid.uuid4().hex[:16].upper(),
        validation_mission_id=validation_id, sequence=sequence, capability=capability,
        status="running", request_json=json.dumps(_sanitize(request), sort_keys=True, default=str),
        started_at=_now(),
    )
    with PlatformSessionLocal() as db:
        db.add(step)
        db.commit()
        db.refresh(step)
        db.expunge(step)
    return step


def _finish_step(step: PlatformValidationStep, verification: Dict[str, Any], authorization: Dict[str, Any], evidence_id: Optional[str], error: Optional[str], duration_ms: int) -> None:
    with PlatformSessionLocal() as db:
        current = db.query(PlatformValidationStep).filter_by(execution_id=step.execution_id).one()
        current.status = "passed" if verification["passed"] else "blocked_by_trust_prerequisite" if verification.get("blocked_by_trust_prerequisite") else "failed"
        current.verification_json = json.dumps(verification, sort_keys=True)
        current.authorization_json = json.dumps(_sanitize(authorization), sort_keys=True, default=str)
        current.evidence_id = evidence_id
        current.error = error
        current.completed_at = _now()
        current.duration_ms = duration_ms
        db.commit()


def _finish_mission(validation_id: str, log: List[Dict[str, Any]], cleanup: Dict[str, Any], final_result: str, started: datetime, workspace_id: Optional[str]) -> None:
    now = _now()
    with PlatformSessionLocal() as db:
        mission = db.query(PlatformValidationMission).filter_by(validation_mission_id=validation_id).one()
        mission.status = "completed" if final_result in {"pass", "blocked_by_trust_prerequisite"} else "failed"
        mission.final_result = final_result
        mission.execution_log_json = json.dumps(log, sort_keys=True)
        mission.verification_json = json.dumps({"passed": final_result == "pass", "steps_executed": len(log)}, sort_keys=True)
        mission.cleanup_json = json.dumps(cleanup, sort_keys=True)
        mission.workspace_id = workspace_id
        mission.completed_at = now
        mission.duration_ms = int((now - started).total_seconds() * 1000)
        mission.updated_at = now
        db.commit()


def _outcome_passed(outcome: Any) -> bool:
    return isinstance(outcome, dict) and (
        str(outcome.get("status") or "").lower() in TERMINAL_SUCCESS
        or outcome.get("acquired") is True
        or outcome.get("renewed") is True
    )


def _run_cleanup(payload: Dict[str, Any], dispatch: Executor, shared: Dict[str, Any]) -> Dict[str, Any]:
    operations = payload.get("cleanup_operations")
    if not isinstance(operations, list) or not operations:
        return {"status": "not-required", "operations": []}
    results = []
    passed = True
    for item in operations:
        if not isinstance(item, dict) or not item.get("capability"):
            passed = False
            results.append({"status": "invalid", "error": "Cleanup capability is required."})
            continue
        request = dict(shared)
        request.update(item.get("payload") or {})
        request.update({"mission_id": shared.get("mission_id"), "actor": payload.get("actor") or "mission_control", "token": payload.get("token"), "execution_mode": payload.get("execution_mode") or "live"})
        try:
            outcome = dispatch(str(item["capability"]), request)
        except Exception as exc:
            outcome = {"status": "failed", "error_type": type(exc).__name__}
        passed = passed and _outcome_passed(outcome)
        results.append(_sanitize({"capability": item["capability"], "status": outcome.get("status"), "evidence_id": _evidence_id(outcome)}))
    return {"status": "completed" if passed else "failed", "operations": results}


def _evidence_id(outcome: Dict[str, Any]) -> Optional[str]:
    evidence = outcome.get("governance_evidence") or outcome.get("execution_evidence") or {}
    return str(evidence.get("evidence_id")) if isinstance(evidence, dict) and evidence.get("evidence_id") else None


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: ("[REDACTED]" if key.lower() in SECRET_KEYS else _sanitize(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value


def _present_step(step: PlatformValidationStep) -> Dict[str, Any]:
    return {"execution_id": step.execution_id, "sequence": step.sequence, "capability": step.capability, "status": step.status, "evidence_id": step.evidence_id, "verification": _loads(step.verification_json, {}), "error": step.error, "duration_ms": step.duration_ms}


def _loads(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, ValueError):
        return fallback


def _types() -> List[str]:
    from app.platform.validation.catalogue import VALIDATION_CATALOGUE
    return sorted(VALIDATION_CATALOGUE)


def _now() -> datetime:
    return datetime.now(timezone.utc)
