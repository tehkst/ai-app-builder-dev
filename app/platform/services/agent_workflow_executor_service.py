from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Set

from sqlalchemy.orm import Session

from app.platform.persistence.models import PlatformAuditEvent
from app.platform.services.agent_execution_planner_service import build_agent_execution_plan
from app.platform.services.agent_execution_bridge_service import execute_agent_via_bridge
from app.platform.services.workflow_run_persistence_service import persist_workflow_result


TERMINAL_STEP_STATUSES = {"completed", "failed", "blocked", "skipped"}

MAX_WORKFLOW_STEPS = 50
MAX_STEP_DEPENDENCIES = 10
MAX_CONTEXT_JSON_BYTES = 20000
MAX_HANDLER_RESULT_JSON_BYTES = 12000


def _log_workflow_event(
    db: Session,
    *,
    status: str,
    metadata: Dict[str, Any],
) -> None:
    event = PlatformAuditEvent(
        event_type="agent_workflow_execution",
        actor_type="system",
        actor_id="agent_workflow_executor_service",
        status=status,
        metadata_json=json.dumps(metadata, sort_keys=True),
    )
    db.add(event)
    db.commit()


def _json_size_bytes(value: Any) -> int:
    return len(json.dumps(value, sort_keys=True, default=str).encode("utf-8"))


def _summarize_oversized_value(value: Any, *, max_bytes: int) -> Dict[str, Any]:
    return {
        "truncated": True,
        "reason": "max_json_bytes_exceeded",
        "original_json_bytes": _json_size_bytes(value),
        "max_json_bytes": max_bytes,
        "summary_type": type(value).__name__,
    }


def _enforce_handler_result_limit(handler_result: Any) -> Any:
    if _json_size_bytes(handler_result) <= MAX_HANDLER_RESULT_JSON_BYTES:
        return handler_result

    return _summarize_oversized_value(
        handler_result,
        max_bytes=MAX_HANDLER_RESULT_JSON_BYTES,
    )


def _validate_workflow_scalability(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    violations: List[Dict[str, Any]] = []

    if len(steps) > MAX_WORKFLOW_STEPS:
        violations.append(
            {
                "reason": "max_workflow_steps_exceeded",
                "step_count": len(steps),
                "max_workflow_steps": MAX_WORKFLOW_STEPS,
            }
        )

    for step in steps:
        requires_steps = step.get("requires_steps") or []
        if len(requires_steps) > MAX_STEP_DEPENDENCIES:
            violations.append(
                {
                    "reason": "max_step_dependencies_exceeded",
                    "step_id": step.get("step_id"),
                    "dependency_count": len(requires_steps),
                    "max_step_dependencies": MAX_STEP_DEPENDENCIES,
                }
            )

    return violations


def _build_blocked_scalability_result(
    *,
    workflow_run_id: str,
    workflow_name: str,
    simulation: bool,
    steps: List[Dict[str, Any]],
    violations: List[Dict[str, Any]],
) -> Dict[str, Any]:
    step_runs = []

    for step in steps:
        step_runs.append(
            {
                "step_run_id": f"step_run_{uuid.uuid4().hex}",
                "step_id": step.get("step_id"),
                "title": step.get("title") or step.get("step_id") or "Untitled Step",
                "required_capability": step.get("required_capability"),
                "requires_steps": step.get("requires_steps") or [],
                "candidate_agents": [],
                "agent_available": False,
                "selected_agent": None,
                "status": "blocked",
                "output": None,
                "error": {
                    "reason": "workflow_scalability_guardrail_violation",
                    "violations": violations,
                },
            }
        )

    return {
        "success": False,
        "workflow_run_id": workflow_run_id,
        "workflow_name": workflow_name,
        "status": "blocked",
        "simulation": simulation,
        "plan_status": "workflow_scalability_guardrail_violation",
        "step_count": len(step_runs),
        "completed_step_count": 0,
        "blocked_step_count": len(step_runs),
        "failed_step_count": 0,
        "missing_capabilities": [],
        "dependency_repair_plan": [],
        "scalability_violations": violations,
        "step_runs": step_runs,
    }


def _create_step_runs(plan: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    step_runs: Dict[str, Dict[str, Any]] = {}

    plan_steps = plan.get("steps") or []
    blocked_steps = plan.get("blocked_steps") or []

    combined_steps: Dict[str, Dict[str, Any]] = {}

    for step in plan_steps:
        step_id = step.get("step_id")
        if step_id:
            combined_steps[step_id] = step

    for step in blocked_steps:
        step_id = step.get("step_id")
        if step_id and step_id not in combined_steps:
            combined_steps[step_id] = step

    for step_id, step in combined_steps.items():
        step_runs[step_id] = {
            "step_run_id": f"step_run_{uuid.uuid4().hex}",
            "step_id": step_id,
            "title": step.get("title") or step_id,
            "required_capability": step.get("required_capability"),
            "requires_steps": step.get("requires_steps") or [],
            "candidate_agents": step.get("candidate_agents") or [],
            "agent_available": bool(step.get("agent_available")),
            "selected_agent": None,
            "status": "queued",
            "output": None,
            "error": None,
        }

    return step_runs


def _dependencies_completed(
    step_run: Dict[str, Any],
    step_runs: Dict[str, Dict[str, Any]],
) -> bool:
    for required_step_id in step_run.get("requires_steps") or []:
        required_step = step_runs.get(required_step_id)
        if not required_step or required_step.get("status") != "completed":
            return False
    return True


def _dependency_failed_or_blocked(
    step_run: Dict[str, Any],
    step_runs: Dict[str, Dict[str, Any]],
) -> bool:
    for required_step_id in step_run.get("requires_steps") or []:
        required_step = step_runs.get(required_step_id)
        if not required_step:
            return True
        if required_step.get("status") in {"failed", "blocked", "skipped"}:
            return True
    return False


def _select_agent_for_step(step_run: Dict[str, Any]) -> Dict[str, Any]:
    candidates = step_run.get("candidate_agents") or []
    selected_agent = candidates[0] if candidates else None
    step_run["selected_agent"] = selected_agent
    return step_run


def _compact_step_output(step_run: Dict[str, Any]) -> Dict[str, Any]:
    output = step_run.get("output") or {}
    bridge_result = output.get("bridge_result") if isinstance(output, dict) else None

    if isinstance(bridge_result, dict):
        return {
            "mode": output.get("mode"),
            "agent_id": bridge_result.get("agent_id"),
            "status": bridge_result.get("status"),
            "success": bridge_result.get("success"),
            "handler_result": _enforce_handler_result_limit(bridge_result.get("handler_result")),
        }

    return {
        "mode": output.get("mode") if isinstance(output, dict) else None,
        "output": output,
    }


def _compact_dependency_step(required_step: Dict[str, Any]) -> Dict[str, Any]:
    selected_agent = required_step.get("selected_agent") or {}

    return {
        "step_id": required_step.get("step_id"),
        "title": required_step.get("title"),
        "status": required_step.get("status"),
        "selected_agent": {
            "agent_id": selected_agent.get("agent_id"),
            "name": selected_agent.get("name"),
        }
        if isinstance(selected_agent, dict)
        else None,
        "output": _compact_step_output(required_step),
    }


def _build_step_workflow_context(
    *,
    workflow_name: str,
    step_run: Dict[str, Any],
    step_runs: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    dependency_outputs: Dict[str, Any] = {}

    for required_step_id in step_run.get("requires_steps") or []:
        required_step = step_runs.get(required_step_id)
        if not required_step:
            continue

        dependency_outputs[required_step_id] = _compact_dependency_step(required_step)

    workflow_context = {
        "workflow_name": workflow_name,
        "mode": "workflow_bridge_integration",
        "current_step": {
            "step_id": step_run.get("step_id"),
            "title": step_run.get("title"),
            "required_capability": step_run.get("required_capability"),
            "requires_steps": step_run.get("requires_steps") or [],
        },
        "dependency_outputs": dependency_outputs,
        "dependency_output_count": len(dependency_outputs),
    }

    if _json_size_bytes(workflow_context) > MAX_CONTEXT_JSON_BYTES:
        workflow_context["dependency_outputs"] = {
            "_truncated": _summarize_oversized_value(
                dependency_outputs,
                max_bytes=MAX_CONTEXT_JSON_BYTES,
            )
        }
        workflow_context["dependency_output_count"] = len(dependency_outputs)
        workflow_context["context_truncated"] = True

    return workflow_context


def _complete_step_simulation(step_run: Dict[str, Any]) -> Dict[str, Any]:
    _select_agent_for_step(step_run)
    selected_agent = step_run.get("selected_agent")
    step_run["status"] = "completed"
    step_run["output"] = {
        "mode": "simulation",
        "message": (
            f"Step '{step_run.get('step_id')}' completed in safe simulation mode."
        ),
        "agent_id": selected_agent.get("agent_id") if selected_agent else None,
        "capability": step_run.get("required_capability"),
    }
    return step_run


def _block_step(step_run: Dict[str, Any], *, reason: str) -> Dict[str, Any]:
    step_run["status"] = "blocked"
    step_run["error"] = {
        "reason": reason,
        "required_capability": step_run.get("required_capability"),
    }
    return step_run


def execute_agent_workflow(
    db: Session,
    *,
    steps: List[Dict[str, Any]],
    workflow_name: str = "Agent Workflow",
    simulation: bool = True,
    log_event: bool = True,
    persist_result: bool = True,
) -> Dict[str, Any]:
    workflow_run_id = f"workflow_run_{uuid.uuid4().hex}"

    scalability_violations = _validate_workflow_scalability(steps)
    if scalability_violations:
        result = _build_blocked_scalability_result(
            workflow_run_id=workflow_run_id,
            workflow_name=workflow_name,
            simulation=simulation,
            steps=steps,
            violations=scalability_violations,
        )

        if persist_result:
            result["persistence"] = persist_workflow_result(
                db,
                result=result,
            )

        if log_event:
            _log_workflow_event(
                db,
                status="blocked",
                metadata={
                    "workflow_run_id": workflow_run_id,
                    "workflow_name": workflow_name,
                    "simulation": simulation,
                    "plan_status": result["plan_status"],
                    "scalability_violations": scalability_violations,
                    "persisted": bool(result.get("persistence", {}).get("persisted")),
                },
            )

        return result

    plan = build_agent_execution_plan(
        db,
        steps=steps,
        log_event=False,
    )

    step_runs = _create_step_runs(plan)

    workflow_status = "created"

    if plan.get("validation_issues"):
        workflow_status = "invalid_plan"
        for step_run in step_runs.values():
            _block_step(step_run, reason="invalid_plan")
    elif plan.get("has_cycle"):
        workflow_status = "dependency_cycle_detected"
        for step_run in step_runs.values():
            _block_step(step_run, reason="dependency_cycle_detected")
    else:
        progress_made = True

        while progress_made:
            progress_made = False

            for step_id in plan.get("execution_order", []):
                step_run = step_runs.get(step_id)
                if not step_run or step_run.get("status") != "queued":
                    continue

                if _dependency_failed_or_blocked(step_run, step_runs):
                    _block_step(step_run, reason="dependency_failed_or_blocked")
                    progress_made = True
                    continue

                if not _dependencies_completed(step_run, step_runs):
                    continue

                if not step_run.get("agent_available"):
                    _block_step(step_run, reason="missing_required_capability")
                    progress_made = True
                    continue

                if simulation:
                    _complete_step_simulation(step_run)
                else:
                    _select_agent_for_step(step_run)
                    step_run["status"] = "running"
                    workflow_context = _build_step_workflow_context(
                        workflow_name=workflow_name,
                        step_run=step_run,
                        step_runs=step_runs,
                    )
                    step_run["workflow_context"] = workflow_context

                    bridge_result = execute_agent_via_bridge(
                        db,
                        workflow_run_id=workflow_run_id,
                        step_run=step_run,
                        workflow_context=workflow_context,
                        safe_mode=True,
                        log_event=log_event,
                    )
                    if bridge_result.get("success"):
                        step_run["status"] = "completed"
                        step_run["output"] = {
                            "mode": "bridge",
                            "bridge_result": bridge_result,
                        }
                        step_run["error"] = None
                    else:
                        step_run["status"] = "failed"
                        step_run["output"] = None
                        step_run["error"] = {
                            "reason": bridge_result.get("status") or "bridge_execution_failed",
                            "bridge_result": bridge_result,
                        }
                progress_made = True

        for step_run in step_runs.values():
            if step_run.get("status") == "queued":
                if _dependency_failed_or_blocked(step_run, step_runs):
                    _block_step(step_run, reason="dependency_failed_or_blocked")
                else:
                    _block_step(step_run, reason="not_reachable")

        statuses = [step_run.get("status") for step_run in step_runs.values()]
        if all(status == "completed" for status in statuses):
            workflow_status = "completed"
        elif any(status == "blocked" for status in statuses):
            workflow_status = "blocked"
        elif any(status == "failed" for status in statuses):
            workflow_status = "failed"
        else:
            workflow_status = "unknown"

    ordered_step_runs = [
        step_runs[step_id]
        for step_id in plan.get("execution_order", [])
        if step_id in step_runs
    ]

    unordered_remaining = [
        step_run
        for step_id, step_run in step_runs.items()
        if step_id not in set(plan.get("execution_order", []))
    ]

    all_step_runs = ordered_step_runs + unordered_remaining

    completed_count = len(
        [step_run for step_run in all_step_runs if step_run.get("status") == "completed"]
    )
    blocked_count = len(
        [step_run for step_run in all_step_runs if step_run.get("status") == "blocked"]
    )
    failed_count = len(
        [step_run for step_run in all_step_runs if step_run.get("status") == "failed"]
    )

    result = {
        "success": workflow_status == "completed",
        "workflow_run_id": workflow_run_id,
        "workflow_name": workflow_name,
        "status": workflow_status,
        "simulation": simulation,
        "plan_status": plan.get("status"),
        "step_count": len(all_step_runs),
        "completed_step_count": completed_count,
        "blocked_step_count": blocked_count,
        "failed_step_count": failed_count,
        "missing_capabilities": plan.get("missing_capabilities", []),
        "dependency_repair_plan": plan.get("dependency_repair_plan", []),
        "step_runs": all_step_runs,
    }

    if persist_result:
        result["persistence"] = persist_workflow_result(
            db,
            result=result,
        )

    if log_event:
        _log_workflow_event(
            db,
            status=workflow_status,
            metadata={
                "workflow_run_id": workflow_run_id,
                "workflow_name": workflow_name,
                "simulation": simulation,
                "step_count": result["step_count"],
                "completed_step_count": completed_count,
                "blocked_step_count": blocked_count,
                "failed_step_count": failed_count,
                "plan_status": result["plan_status"],
                "persisted": bool(result.get("persistence", {}).get("persisted")),
                "max_workflow_steps": MAX_WORKFLOW_STEPS,
                "max_step_dependencies": MAX_STEP_DEPENDENCIES,
                "max_context_json_bytes": MAX_CONTEXT_JSON_BYTES,
                "max_handler_result_json_bytes": MAX_HANDLER_RESULT_JSON_BYTES,
            },
        )

    return result
