from __future__ import annotations

import ast
from pathlib import Path


def get_function_source(path: str, function_name: str) -> str:
    text = Path(path).read_text()
    tree = ast.parse(text)

    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return ast.get_source_segment(text, node)

    raise RuntimeError(f"Function {function_name} not found in {path}")


def assert_order(body: str, first: str, second: str, label: str):
    a = body.find(first)
    b = body.find(second)

    assert a >= 0, f"{label}: '{first}' not found"
    assert b >= 0, f"{label}: '{second}' not found"
    assert a < b, f"{label}: publication occurs before persistence"


def main():
    body = get_function_source(
        "app/platform/services/agent_task_service/part_2.py",
        "create_agent_task",
    )

    assert_order(
        body,
        "db.commit()",
        "publish_agent_task_lifecycle(",
        "create_agent_task",
    )

    body = get_function_source(
        "app/platform/services/agent_task_service/part_3.py",
        "update_agent_task_status",
    )

    assert "publish_agent_task_lifecycle(" in body

    body = get_function_source(
        "app/platform/operating_console/mission_run_service.py",
        "_enqueue",
    )

    assert_order(
        body,
        "db.commit()",
        "publish_agent_task_lifecycle(",
        "_enqueue",
    )

    print("agent task canonical lifecycle boundaries: PASS")


if __name__ == "__main__":
    main()
