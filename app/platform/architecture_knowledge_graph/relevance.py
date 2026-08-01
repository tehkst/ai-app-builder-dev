"""What's relevant to a given file/module - direct dependencies, direct dependents,
and (Phase 3) which functions call into it.

Deliberately built from project_repository() + project_symbols() directly rather
than build_graph(): both are pure AST + filesystem, no database and no server, so
this is fast and safe to run in any Claude Code session with just a checkout - see
CLAUDE.md. Run as a plain CLI:

    python -m app.platform.architecture_knowledge_graph.relevance <path/to/file.py>
"""
from __future__ import annotations

import sys
from typing import Any, Dict, List

from app.platform.architecture_knowledge_graph.repository_projection import project_repository
from app.platform.architecture_knowledge_graph.symbol_projection import project_symbols


def _module_name(path: str) -> str:
    normalized = str(path).strip().replace("\\", "/").lstrip("/")
    if normalized.endswith(".py"):
        normalized = normalized[:-3]
    return normalized.replace("/", ".")


def _strip(node_id: str) -> str:
    return node_id.split(":", 1)[-1]


def query_relevance(path: str) -> Dict[str, Any]:
    module = _module_name(path)
    module_id = "module:%s" % module

    repo = project_repository()
    symbols = project_symbols()
    nodes = {node["id"]: node for node in repo["nodes"] + symbols["nodes"]}
    edges = repo["edges"] + symbols["edges"]

    if module_id not in nodes:
        return {
            "status": "not-found",
            "module": module,
            "message": (
                "No module node found for %r. Confirm the path is a real .py file "
                "under app/ (e.g. app/platform/foo/bar.py)." % path
            ),
        }

    module_node = nodes[module_id]
    depends_on = sorted({
        edge["target"] for edge in edges
        if edge["source"] == module_id and edge["type"] == "imports" and edge["target"] in nodes
    })
    depended_on_by = sorted({
        edge["source"] for edge in edges
        if edge["target"] == module_id and edge["type"] == "imports" and edge["source"] in nodes
    })
    defined_here = sorted(
        node["id"] for node in symbols["nodes"] if node.get("path") == module_node.get("path")
    )
    defined_here_set = set(defined_here)
    external_callers = sorted({
        edge["source"] for edge in edges
        if edge["type"] == "calls" and edge["target"] in defined_here_set and edge["source"] not in defined_here_set
    })
    quality = module_node.get("quality") or {}

    return {
        "status": "found",
        "module": module,
        "path": module_node.get("path"),
        "loc": quality.get("loc"),
        "line_rule": quality.get("line_rule"),
        "depends_on": [_strip(node_id) for node_id in depends_on],
        "depended_on_by": [_strip(node_id) for node_id in depended_on_by],
        "defined_functions_and_classes": [_strip(node_id) for node_id in defined_here],
        "external_callers_of_its_functions": [_strip(node_id) for node_id in external_callers],
        "related_tests": quality.get("tests") or [],
    }


def render_report(result: Dict[str, Any]) -> str:
    if result["status"] == "not-found":
        return result["message"]
    lines: List[str] = [
        "Relevance report for %s" % result["module"],
        "  path: %s (loc=%s, line_rule=%s)" % (result["path"], result["loc"], result["line_rule"]),
        "",
        "Depends on (%d):" % len(result["depends_on"]),
    ]
    lines += ["  - %s" % item for item in result["depends_on"]] or ["  (none)"]
    lines += ["", "Depended on by / imported by (%d):" % len(result["depended_on_by"])]
    lines += ["  - %s" % item for item in result["depended_on_by"]] or ["  (none)"]
    lines += ["", "Functions/classes defined here (%d):" % len(result["defined_functions_and_classes"])]
    lines += ["  - %s" % item for item in result["defined_functions_and_classes"][:30]] or ["  (none)"]
    lines += ["", "External callers of this module's functions (%d, unambiguous matches only):"
              % len(result["external_callers_of_its_functions"])]
    lines += ["  - %s" % item for item in result["external_callers_of_its_functions"][:30]] or ["  (none)"]
    if result["related_tests"]:
        lines += ["", "Related tests:"]
        lines += ["  - %s" % item for item in result["related_tests"]]
    return "\n".join(lines)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m app.platform.architecture_knowledge_graph.relevance <path/to/file.py>")
        raise SystemExit(1)
    print(render_report(query_relevance(sys.argv[1])))


if __name__ == "__main__":
    main()
