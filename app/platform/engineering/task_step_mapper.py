from __future__ import annotations


def task_graph_to_steps(task_graph: dict, app_request: str) -> dict:
    steps = []
    for task in task_graph.get("tasks", []):
        step_id = str(task.get("task_id") or "")
        capability = str(task.get("capability") or "")
        steps.append(
            {
                "step_id": step_id,
                "title": "Task: " + step_id.replace("_", " ").title(),
                "description": "Execute scoped task for request: " + app_request,
                "required_capability": _runtime_capability(capability, step_id),
                "requires_steps": list(task.get("depends_on") or []),
                "input": {
                    "app_request": app_request,
                    "task_graph_id": task_graph.get("graph_id"),
                    "source_task_id": step_id,
                    "source_capability": capability,
                },
            }
        )
    return {
        "success": True,
        "workflow_version": "v101-backend-builder",
        "workflow_name": "Task Graph: " + app_request[:80],
        "app_request": app_request,
        "step_count": len(steps),
        "steps": steps,
    }


def _runtime_capability(capability: str, step_id: str = "") -> str:
    if step_id == "architecture":
        return "architect_task"
    if step_id == "review":
        return "reviewer_task"
    if step_id == "backend_contract":
        return "backend_builder_task"
    if step_id == "data_model":
        return "database_builder_task"
    if step_id == "frontend_shell":
        return "frontend_builder_task"
    if capability.startswith("customer.backend"):
        return "backend_builder_task"
    if capability.startswith("customer.database"):
        return "database_builder_task"
    if capability.startswith("customer.frontend"):
        return "frontend_builder_task"
    if capability.startswith("customer.testing"):
        return "test_task"
    if capability.startswith("platform.scope"):
        return "architect_task"
    if capability.startswith("platform.builder"):
        return "builder_task"
    if capability.startswith("platform.validator"):
        return "reviewer_task"
    if capability.startswith("platform.testing"):
        return "test_task"
    if capability.startswith("platform.documentation"):
        return "reviewer_task"
    return "reviewer_task"
