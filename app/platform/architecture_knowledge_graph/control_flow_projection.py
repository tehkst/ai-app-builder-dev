from __future__ import annotations

import ast
from typing import Any, Dict, List, Tuple

from app.platform.architecture_knowledge_graph.repository_projection import REPO_ROOT, _python_paths
from app.platform.architecture_knowledge_graph.symbol_projection import (
    MAX_DEFINITIONS_PER_MODULE,
    _collect_definitions,
    _module_name,
)

PATH_COUNT_CAP = 10_000

# Structural pattern matching (ast.Match/match_case) is Python 3.10+ only - this platform's
# production Dockerfile is pinned to python:3.9-slim, so referencing ast.Match unconditionally
# would raise AttributeError the moment this module is imported there. getattr(..., None) keeps
# this file importable on 3.9 while still counting match/case branches wherever this does run
# on 3.10+ (e.g. local dev).
_MATCH_TYPE = getattr(ast, "Match", None)
_NESTED_SCOPE_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)


def project_control_flow() -> Dict[str, Dict[str, Any]]:
    """Per-function control-flow metrics, joined onto symbol_projection.py's Function
    nodes by id in analysis.py's enrich_graph().

    Deliberately reuses symbol_projection._collect_definitions rather than re-walking the
    AST independently: that function has non-obvious semantics (a definitions-per-module
    cap, one-level-only class-method nesting, a specific id format) that a second, separate
    implementation would have to reproduce exactly to join correctly - any future drift
    between two independent walks would be a silent, undetectable bug rather than a loud one.
    This does cost a second full-repo ast.parse pass (real, not free), which is the accepted
    trade-off for correctness over duplication.
    """
    result: Dict[str, Dict[str, Any]] = {}
    for path in _python_paths():
        module = _module_name(path)
        try:
            tree = ast.parse((REPO_ROOT / path).read_text(encoding="utf-8"))
        except (SyntaxError, OSError, UnicodeError):
            continue
        definitions = _collect_definitions(tree, module)[:MAX_DEFINITIONS_PER_MODULE]
        for definition in definitions:
            if definition["type"] != "Function":
                continue
            result[definition["id"]] = _analyze(definition["node"])
    return result


def _analyze(func_node: ast.AST) -> Dict[str, Any]:
    decision_points = _count_decision_points(func_node)
    path_count, capped = _count_paths(list(func_node.body))
    return {
        "decision_points": decision_points,
        "cyclomatic_complexity": decision_points + 1,
        "path_count": path_count,
        "path_count_capped": capped,
    }


def _count_decision_points(root: ast.AST) -> int:
    """Exact, uncapped count of real alternative-path constructs in this function's own
    body - never descends into a nested function/lambda/class definition's own body (its
    branches belong to it, not to the enclosing function; mirrors symbol_projection.py's
    _call_sites()'s already-accepted "don't attribute nested scopes to the enclosing
    definition" trade-off). Counts statement-level branches (if/elif chains, for/while,
    try/except, match/case) PLUS expression-level branches (and/or short-circuit, ternary,
    comprehension filters) - idiomatic Python leans on the latter instead of if-statements,
    so excluding them would undercount exactly the code that uses them most.
    """
    count = 0
    stack: List[ast.AST] = list(ast.iter_child_nodes(root))
    while stack:
        node = stack.pop()
        if isinstance(node, _NESTED_SCOPE_TYPES):
            continue
        if isinstance(node, ast.If):
            count += 1
        elif isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
            count += 1
        elif isinstance(node, ast.Try):
            count += len(node.handlers)
        elif _MATCH_TYPE is not None and isinstance(node, _MATCH_TYPE):
            count += max(len(node.cases) - 1, 0)
        elif isinstance(node, ast.BoolOp):
            count += max(len(node.values) - 1, 0)
        elif isinstance(node, ast.IfExp):
            count += 1
        elif isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            for generator in node.generators:
                count += len(generator.ifs)
        stack.extend(ast.iter_child_nodes(node))
    return count


def _count_paths(stmts: List[ast.stmt]) -> Tuple[int, bool]:
    """Structural path count through a statement sequence: sequential statements'
    path-counts multiply (each is an independent choice passed through in series); an
    if/elif/else's alternatives sum (exactly one is taken). Loops are modeled as a binary
    "entered vs skipped" choice, not per-iteration - a deliberate simplification. Only
    statement-level branches (if/for/while/try/match) are counted here - expression-level
    branches (and/or, ternary, comprehension filters) are counted in decision_points /
    cyclomatic_complexity but not multiplied into this path count, to keep this recursion's
    semantics tractable and honest about its own scope. Capped at PATH_COUNT_CAP - ordinary
    Python (e.g. a chain of independent early-return guard clauses) multiplies past a small
    cap almost immediately, so the cap is real and reported explicitly, never silently wrong.
    """
    total = 1
    capped = False
    for stmt in stmts:
        stmt_count, stmt_capped = _stmt_paths(stmt)
        capped = capped or stmt_capped
        total *= stmt_count
        if total >= PATH_COUNT_CAP:
            total = PATH_COUNT_CAP
            capped = True
    return total, capped


def _stmt_paths(stmt: ast.stmt) -> Tuple[int, bool]:
    if isinstance(stmt, ast.If):
        true_count, true_capped = _count_paths(stmt.body)
        false_count, false_capped = _count_paths(stmt.orelse) if stmt.orelse else (1, False)
        total = true_count + false_count
        return min(total, PATH_COUNT_CAP), (true_capped or false_capped or total >= PATH_COUNT_CAP)
    if isinstance(stmt, (ast.For, ast.AsyncFor, ast.While)):
        body_count, body_capped = _count_paths(stmt.body)
        total = 1 + body_count
        return min(total, PATH_COUNT_CAP), (body_capped or total >= PATH_COUNT_CAP)
    if isinstance(stmt, ast.Try):
        total, capped = _count_paths(stmt.body)
        for handler in stmt.handlers:
            handler_count, handler_capped = _count_paths(handler.body)
            total += handler_count
            capped = capped or handler_capped
        if stmt.orelse:
            orelse_count, orelse_capped = _count_paths(stmt.orelse)
            total += orelse_count
            capped = capped or orelse_capped
        return min(total, PATH_COUNT_CAP), (capped or total >= PATH_COUNT_CAP)
    if _MATCH_TYPE is not None and isinstance(stmt, _MATCH_TYPE):
        total = 0
        capped = False
        for case in stmt.cases:
            case_count, case_capped = _count_paths(case.body)
            total += case_count
            capped = capped or case_capped
        return min(max(total, 1), PATH_COUNT_CAP), (capped or total >= PATH_COUNT_CAP)
    return 1, False
