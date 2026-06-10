from __future__ import annotations

from typing import Any, Dict

from app.platform.services.agent_workflow_json import json_size_bytes, summarize_oversized_value
from app.platform.services.agent_workflow_limits import MAX_CONTEXT_JSON_BYTES, MAX_HANDLER_RESULT_JSON_BYTES


def enforce_handler_result_limit(handler_result: Any) -> Any:
    if json_size_bytes(handler_result) <= MAX_HANDLER_RESULT_JSON_BYTES:
        return handler_result
    return summarize_oversized_value(handler_result, max_bytes=MAX_HANDLER_RESULT_JSON_BYTES)


def compact_step_output(step_run: Dict[str, Any]) -> Dict[str, Any]:
    output = step_run.get("output") or {}
    bridge_result = output.get("bridge_result") if isinstance(output, dict) else None
    if isinstance(bridge_result, dict):
        return {
            "mode": output.get("mode"),
            "agent_id": bridge_result.get("agent_id"),
            "status": bridge_result.get("status"),
            "success": bridge_result.get("success"),
            "handler_result": enforce_handler_result_limit(bridge_result.get("handler_result")),
        }
    return {"mode": output.get("mode") if isinstance(output, dict) else None, "output": output}


def build_step_workflow_context(
    *,
    workflow_name: str,
    step_run: Dict[str, Any],
    step_runs: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    dependency_outputs: Dict[str, Any] = {}
    for required_step_id in step_run.get("requires_steps") or []:
        required_step = step_runs.get(required_step_id)
        if required_step:
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
    if json_size_bytes(workflow_context) > MAX_CONTEXT_JSON_BYTES:
        workflow_context["dependency_outputs"] = {
            "_truncated": summarize_oversized_value(
                dependency_outputs,
                max_bytes=MAX_CONTEXT_JSON_BYTES,
            )
        }
        workflow_context["dependency_output_count"] = len(dependency_outputs)
        workflow_context["context_truncated"] = True
    return workflow_context


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
        "output": compact_step_output(required_step),
    }
