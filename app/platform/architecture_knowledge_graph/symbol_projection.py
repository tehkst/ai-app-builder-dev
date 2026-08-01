from __future__ import annotations

import ast
from typing import Any, Dict, List

from app.platform.architecture_knowledge_graph.repository_projection import REPO_ROOT, _python_paths
from app.platform.coding_agent.dependency_analyzer import _call_name

MAX_DEFINITIONS_PER_MODULE = 40


def project_symbols() -> Dict[str, Any]:
    """Function/class-level nodes and best-effort 'calls' edges (Phase 3, VIEW_TYPES['code']).

    Two passes, mirroring dependency_analyzer.py's proven CallVisitor pattern (current-
    function tracking) rather than inventing new AST-walking logic: pass one collects every
    module's real function/class/method definitions into a repo-wide symbol table (bare
    name -> definition ids); pass two walks each definition's own body for call sites and
    resolves each callee name against that table. A call only becomes an edge when exactly
    one repo-wide definition matches that bare name - an ambiguous name (the same function
    name defined in several modules) is real uncertainty, not resolvable by this static,
    no-type-inference analysis, so it is dropped rather than guessing a specific target.
    """
    paths = _python_paths()
    trees: Dict[str, ast.AST] = {}
    definitions_by_module: Dict[str, List[Dict[str, Any]]] = {}
    symbol_table: Dict[str, List[str]] = {}

    for path in paths:
        module = _module_name(path)
        try:
            tree = ast.parse((REPO_ROOT / path).read_text(encoding="utf-8"))
        except (SyntaxError, OSError, UnicodeError):
            continue
        trees[module] = tree
        definitions = _collect_definitions(tree, module)[:MAX_DEFINITIONS_PER_MODULE]
        definitions_by_module[module] = definitions
        for definition in definitions:
            symbol_table.setdefault(definition["bare_name"], []).append(definition["id"])

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, str]] = []
    for path in paths:
        module = _module_name(path)
        definitions = definitions_by_module.get(module) or []
        module_node_id = "module:%s" % module
        for definition in definitions:
            nodes.append(_definition_node(definition, path))
            edges.append(_edge(module_node_id, definition["id"], "defines", "python-ast"))
        for definition in definitions:
            for callee_name in _call_sites(definition["node"]):
                targets = [t for t in symbol_table.get(callee_name) or [] if t != definition["id"]]
                if len(targets) == 1:
                    edges.append(_edge(
                        definition["id"], targets[0], "calls",
                        "python-ast-call-site (high confidence: single repo-wide match)",
                    ))
    return {"nodes": nodes, "edges": _unique_edges(edges)}


def _module_name(path: str) -> str:
    return path[:-3].replace("/", ".")


def _collect_definitions(tree: ast.AST, module: str) -> List[Dict[str, Any]]:
    definitions: List[Dict[str, Any]] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            definitions.append(_definition(module, node.name, "Function", node))
        elif isinstance(node, ast.ClassDef):
            definitions.append(_definition(module, node.name, "Class", node))
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    qualified = "%s.%s" % (node.name, child.name)
                    definitions.append(_definition(module, qualified, "Function", child, bare_name=child.name))
    return definitions


def _definition(module: str, qualified_name: str, node_type: str, node: ast.AST, bare_name: str = None) -> Dict[str, Any]:
    return {
        "id": "%s:%s.%s" % (node_type.lower(), module, qualified_name),
        "module": module,
        "qualified_name": qualified_name,
        "bare_name": bare_name or qualified_name,
        "type": node_type,
        "node": node,
        "lineno": getattr(node, "lineno", None),
    }


def _definition_node(definition: Dict[str, Any], path: str) -> Dict[str, Any]:
    return {
        "id": definition["id"],
        "type": definition["type"],
        "name": "%s.%s" % (definition["module"], definition["qualified_name"]),
        "path": path,
        "authority": "Adapter",
        "lifecycle": "Active",
        "technology": {"language": "Python"},
        "quality": {"line": definition["lineno"]},
        "ownership": {"repository": "tehkst/ai-app-builder-dev"},
        "operational": {},
        "evidence": [{"source": "%s:%s" % (path, definition["lineno"]), "kind": "repository-file"}],
    }


def _call_sites(root: ast.AST) -> List[str]:
    """Bare callee names for every Call inside this definition's body.

    Uses ast.walk (includes nested function/lambda bodies), so a call made inside a
    nested closure is attributed to its enclosing named definition too - a minor
    over-attribution, acceptable for a best-effort signal that already only keeps
    unambiguous, single-match edges.
    """
    calls: List[str] = []
    for node in ast.walk(root):
        if isinstance(node, ast.Call):
            called = _call_name(node)
            if called:
                calls.append(called.split(".")[-1])
    return calls


def _edge(source: str, target: str, relation: str, evidence: str) -> Dict[str, str]:
    return {"source": source, "target": target, "type": relation, "evidence": evidence}


def _unique_edges(edges: List[Dict[str, str]]) -> List[Dict[str, str]]:
    unique = {(edge["source"], edge["target"], edge["type"]): edge for edge in edges}
    return [unique[key] for key in sorted(unique)]
