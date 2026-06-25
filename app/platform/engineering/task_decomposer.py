from __future__ import annotations

from app.platform.engineering.scope_contract import ScopeContract


def v99_task_decomposer_status() -> dict:
    return {"success": True, "status": "active", "version": "v99.1"}


def decompose_scope_contract(scope_contract: ScopeContract) -> dict:
    tasks = _product_tasks() if scope_contract.division == "product" else _platform_tasks()
    graph = {
        "success": True,
        "version": "v99.1",
        "graph_id": "task_graph_" + scope_contract.scope_contract_id.replace("scope_contract_", ""),
        "goal": scope_contract.goal,
        "division": scope_contract.division,
        "work_type": scope_contract.work_type,
        "task_count": len(tasks),
        "tasks": tasks,
    }
    return _validate_graph(graph)


def _product_tasks() -> list:
    return [
        {"task_id": "architecture", "capability": "customer.backend", "depends_on": []},
        {"task_id": "backend_contract", "capability": "customer.backend", "depends_on": ["architecture"]},
        {"task_id": "data_model", "capability": "customer.database", "depends_on": ["architecture"]},
        {"task_id": "frontend_shell", "capability": "customer.frontend", "depends_on": ["backend_contract"]},
        {"task_id": "test_contract", "capability": "customer.testing", "depends_on": ["backend_contract", "data_model", "frontend_shell"]},
        {"task_id": "review", "capability": "customer.testing", "depends_on": ["test_contract"]},
        {"task_id": "release_readiness", "capability": "customer.testing", "depends_on": ["review"]},
    ]


def _platform_tasks() -> list:
    return [
        {"task_id": "scope_design", "capability": "platform.scope", "depends_on": []},
        {"task_id": "implementation_preview", "capability": "platform.builder", "depends_on": ["scope_design"]},
        {"task_id": "compatibility_validation", "capability": "platform.validator", "depends_on": ["implementation_preview"]},
        {"task_id": "regression_test", "capability": "platform.testing", "depends_on": ["compatibility_validation"]},
        {"task_id": "documentation", "capability": "platform.documentation", "depends_on": ["scope_design"]},
        {"task_id": "review", "capability": "platform.validator", "depends_on": ["regression_test", "documentation"]},
        {"task_id": "rollout_readiness", "capability": "platform.testing", "depends_on": ["review"]},
    ]


def _validate_graph(graph: dict) -> dict:
    ids = set([task.get("task_id") for task in graph.get("tasks", [])])
    issues = []
    for task in graph.get("tasks", []):
        for dependency_id in task.get("depends_on", []):
            if dependency_id not in ids:
                issues.append({"task_id": task.get("task_id"), "reason": "unknown_dependency"})
    graph["valid"] = not issues
    graph["validation_issues"] = issues
    return graph
