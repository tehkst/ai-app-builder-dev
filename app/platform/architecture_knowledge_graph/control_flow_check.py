from __future__ import annotations

import ast

from app.platform.architecture_knowledge_graph.control_flow_projection import (
    PATH_COUNT_CAP,
    _analyze,
    project_control_flow,
)
from app.platform.architecture_knowledge_graph.projection import build_graph, reset_projection_cache


def _func(source: str) -> ast.AST:
    return ast.parse(source).body[0]


def main() -> None:
    no_branches = _analyze(_func("def f(x):\n    return x\n"))
    assert no_branches == {
        "decision_points": 0, "cyclomatic_complexity": 1, "path_count": 1, "path_count_capped": False,
    }, no_branches

    if_else = _analyze(_func("def f(x):\n    if x:\n        return 1\n    else:\n        return 2\n"))
    assert if_else["decision_points"] == 1 and if_else["cyclomatic_complexity"] == 2
    assert if_else["path_count"] == 2 and not if_else["path_count_capped"]

    nested_if = _analyze(_func(
        "def f(x, y):\n    if x:\n        if y:\n            return 1\n        return 2\n    return 3\n"
    ))
    assert nested_if["decision_points"] == 2 and nested_if["path_count"] == 3

    # BoolOp/ternary are counted as real alternative paths (decision_points /
    # cyclomatic_complexity) but NOT multiplied into the statement-level path_count,
    # which only models if/for/while/try/match - documented scope, not an oversight.
    boolop = _analyze(_func("def f(x, default):\n    return x or default\n"))
    assert boolop["decision_points"] == 1 and boolop["path_count"] == 1
    ternary = _analyze(_func("def f(x):\n    return 1 if x else 2\n"))
    assert ternary["decision_points"] == 1 and ternary["path_count"] == 1

    # A chain of independent guard clauses is ordinary Python, not a pathological
    # edge case - confirms the cap fires honestly (path_count_capped=True) rather
    # than silently overflowing or under-reporting.
    guard_lines = ["def f(" + ", ".join("v%d" % i for i in range(15)) + "):"]
    guard_lines += ["    if v%d: return %d" % (i, i) for i in range(15)]
    guard_lines.append("    return -1")
    many_guards = _analyze(_func("\n".join(guard_lines) + "\n"))
    assert many_guards["decision_points"] == 15 and many_guards["cyclomatic_complexity"] == 16
    assert many_guards["path_count"] == PATH_COUNT_CAP and many_guards["path_count_capped"] is True

    # Nested function/lambda bodies are not attributed to the enclosing function.
    nested_scope = _analyze(_func(
        "def f(x):\n    def inner(y):\n        if y:\n            return 1\n        return 2\n    return inner(x)\n"
    ))
    assert nested_scope["decision_points"] == 0, nested_scope

    by_id = project_control_flow()
    assert by_id, "no functions found in the repository at all"
    assert all(
        isinstance(value["decision_points"], int) and value["decision_points"] >= 0
        for value in by_id.values()
    ), "a non-negative exact integer is expected for every analyzed function - no fabricated placeholders"

    reset_projection_cache()
    graph = build_graph(refresh=True)
    functions = [node for node in graph["nodes"] if node["type"] == "Function"]
    assert functions, "no Function nodes in the real graph"
    assert all(node.get("control_flow") is not None for node in functions), (
        "every real Function node must carry control_flow data (or an explicit "
        "'unavailable' status) - never a silent gap"
    )
    non_module_types = {node["type"] for node in graph["nodes"] if node["type"] != "Function"}
    assert all(
        node.get("control_flow") is None
        for node in graph["nodes"]
        if node["type"] in non_module_types
    ), "control_flow should only be attached to Function-type nodes"
    print("CONTROL FLOW PROJECTION CHECK PASSED")


if __name__ == "__main__":
    main()
