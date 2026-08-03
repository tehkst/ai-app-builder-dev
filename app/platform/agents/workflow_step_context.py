from __future__ import annotations

from typing import Any, Dict, List

"""Shared helpers for reading a bridge-executed step's own goal and its upstream
dependency outputs from a task payload. Moved out of specialists.py so both it and
management_agents/ can depend on this without importing each other (specialists
registers the management handlers; the handlers need these same lookups).
"""


def _goal(task: Dict[str, Any]) -> str:
    # Prefer the step's own real, full description over the workflow's display
    # name: generate_app_build_workflow's resolved_workflow_name truncates the app
    # request to 80 chars purely for a short UI title - reusing that truncated
    # string as the actual reasoning content fed to a review agent cut its context
    # off mid-sentence (e.g. a CEO review judging a fragment instead of the real,
    # untruncated request). Each step already carries its own full description.
    description = str(task.get("description") or "").strip()
    if description:
        return description

    input_payload = task.get("input_payload") or {}
    workflow_context = input_payload.get("workflow_context") or {}
    workflow_name = str(workflow_context.get("workflow_name") or "")

    if workflow_name.startswith("Build App: "):
        return workflow_name.removeprefix("Build App: ").strip() or "No goal provided"

    return str(input_payload.get("goal") or task.get("title") or "No goal provided")


def _source_task_id(task: Dict[str, Any]) -> str:
    input_payload = task.get("input_payload") or {}
    return str(input_payload.get("step_id") or input_payload.get("source_task_id") or "")


def _dependency_context(task: Dict[str, Any]) -> Dict[str, Any]:
    input_payload = task.get("input_payload") or {}
    workflow_context = input_payload.get("workflow_context") or {}

    dependency_outputs = (
        workflow_context.get("dependency_outputs")
        or input_payload.get("dependency_outputs")
        or {}
    )

    source_steps: List[str] = []
    source_agents: List[str] = []

    if isinstance(dependency_outputs, dict):
        items = dependency_outputs.items()
        dependency_count = len(dependency_outputs)
    else:
        items = [("", dependency) for dependency in dependency_outputs]
        dependency_count = len(dependency_outputs)

    for step_key, dependency in items:
        if not isinstance(dependency, dict):
            continue

        step_id = dependency.get("step_id") or step_key
        selected_agent = dependency.get("selected_agent") or {}
        output = dependency.get("output") or {}
        agent_id = selected_agent.get("agent_id") or output.get("agent_id")

        if step_id:
            source_steps.append(str(step_id))
        if agent_id:
            source_agents.append(str(agent_id))

    return {
        "dependency_output_count": dependency_count,
        "source_steps": source_steps,
        "source_agents": source_agents,
        "context_available": dependency_count > 0,
    }


def _dependency_output_for_step(task: Dict[str, Any], step_id: str) -> Dict[str, Any]:
    """Return the named prior step's own handler_result payload.

    _dependency_context above only summarizes dependency metadata (counts, step
    ids, agent ids). Callers that need the actual artifact (e.g. the architect's
    architecture_plan, or the builder's generated_files) need
    dependency["output"]["handler_result"] (for bridge-executed steps), which
    agent_workflow_context.compact_step_output nests one level deeper than
    dependency["output"] itself.
    """
    input_payload = task.get("input_payload") or {}
    workflow_context = input_payload.get("workflow_context") or {}
    dependency_outputs = (
        workflow_context.get("dependency_outputs")
        or input_payload.get("dependency_outputs")
        or {}
    )

    items = dependency_outputs.items() if isinstance(dependency_outputs, dict) else [("", dependency) for dependency in dependency_outputs]
    for step_key, dependency in items:
        if not isinstance(dependency, dict):
            continue
        if str(dependency.get("step_id") or step_key) == step_id:
            output = dependency.get("output") or {}
            handler_result = output.get("handler_result") if isinstance(output, dict) else None
            if isinstance(handler_result, dict):
                return handler_result
            fallback = output.get("output") if isinstance(output, dict) else None
            return fallback if isinstance(fallback, dict) else {}
    return {}
