from __future__ import annotations

import ast
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from app.platform.coding_agent.dependency_analyzer import build_dependency_graph
from app.platform.architecture_knowledge_graph.node_classification import classify_module

# Repository file-size rule (CLAUDE.md): aim for ~300 lines, split by responsibility;
# above this hard limit a module is flagged "Split Required".
MAX_MODULE_LINES = 500


REPO_ROOT = Path(__file__).resolve().parents[3]


def project_repository() -> Dict[str, Any]:
    paths = _python_paths()
    raw_edges = build_dependency_graph(str(REPO_ROOT), paths, max_files=len(paths) + 1)
    freshness = _last_modified_by_path()
    nodes = [_module_node(path, freshness) for path in paths]
    known = {node["id"] for node in nodes}
    edges = []
    for raw in raw_edges:
        source = "module:%s" % raw["source"]
        target = "module:%s" % raw["target"]
        if source in known and target in known:
            edges.append(_edge(source, target, "imports", "python-ast"))
    for node in nodes:
        for test_path in node["quality"]["tests"]:
            test_id = "module:%s" % test_path[:-3].replace("/", ".")
            if test_id in known:
                edges.append(_edge(test_id, node["id"], "validates", "test-name-evidence"))
    return {"nodes": nodes, "edges": _unique_edges(edges)}


def _python_paths() -> List[str]:
    return [
        str(path.relative_to(REPO_ROOT))
        for path in sorted((REPO_ROOT / "app").rglob("*.py"))
        if "__pycache__" not in path.parts
    ]


def _module_node(path: str, freshness: Dict[str, str]) -> Dict[str, Any]:
    source_path = REPO_ROOT / path
    content = source_path.read_text(encoding="utf-8")
    loc = len(content.splitlines())
    complexity = _complexity(content)
    module = path[:-3].replace("/", ".")
    tests = _related_tests(path)
    authority, extra_evidence = classify_module(path, content, repo_root=REPO_ROOT)
    return {
        "id": "module:%s" % module,
        "type": "Module",
        "name": module,
        "path": path,
        "authority": authority,
        "lifecycle": "Active",
        "technology": {"language": "Python", "version": "3.9+"},
        "quality": {
            "loc": loc,
            "complexity": complexity,
            "line_rule": "Split Required" if loc > MAX_MODULE_LINES else "Compliant",
            "tests": tests,
            "coverage": "Unknown",
            "validation": "Mapped" if tests else "Unverified",
        },
        "ownership": {"repository": "tehkst/ai-app-builder-dev"},
        "operational": {
            "runtime_usage": "Derived from inbound references",
            "production_usage": "Unproven",
            "last_modified": freshness.get(path),
        },
        "evidence": [{"source": path, "kind": "repository-file"}] + extra_evidence,
    }


def _last_modified_by_path() -> Dict[str, str]:
    """Real per-file freshness - distinguishes actively-maintained code from
    long-abandoned files, the same thing a manual file-cleanup audit would
    otherwise have to work out by hand. A naive `git log -1 -- <path>` per file
    was tried first and measured at ~58s for this repo's ~1,270 Python files -
    slower than build_graph()'s own 60s cache TTL, so every cache-miss request
    would pay nearly a full minute for this one signal alone. One batched
    `git log --name-only` walk of the whole history (~0.2s, scoped to app/)
    delivers the identical per-file result - git already emits newest-first, so
    the first time a path is seen is its most recent modification. Degrades to
    an empty dict (every path renders "Unknown", never a fabricated date) if
    git is unavailable."""
    try:
        completed = subprocess.run(
            ["git", "log", "--format=%x00%cI", "--name-only", "--", "app"],
            cwd=str(REPO_ROOT), timeout=15, capture_output=True, text=True,
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    if completed.returncode != 0:
        return {}
    freshness: Dict[str, str] = {}
    for block in completed.stdout.split("\x00"):
        lines = block.splitlines()
        if not lines or not lines[0]:
            continue
        timestamp = lines[0]
        for file_path in lines[1:]:
            file_path = file_path.strip()
            if file_path and file_path not in freshness:
                freshness[file_path] = timestamp
    return freshness


def _complexity(content: str) -> int:
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return 0
    branches = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.BoolOp)
    return 1 + sum(1 for node in ast.walk(tree) if isinstance(node, branches))


def _related_tests(path: str) -> List[str]:
    stem = Path(path).stem
    candidates = []
    for test_path in (REPO_ROOT / "app").rglob("*.py"):
        name = test_path.name
        if stem in name and ("test" in name or "check" in name):
            candidates.append(str(test_path.relative_to(REPO_ROOT)))
    return sorted(candidates)[:12]


def _edge(source: str, target: str, relation: str, evidence: str) -> Dict[str, str]:
    return {"source": source, "target": target, "type": relation, "evidence": evidence}


def _unique_edges(edges: List[Dict[str, str]]) -> List[Dict[str, str]]:
    unique = {(edge["source"], edge["target"], edge["type"]): edge for edge in edges}
    return [unique[key] for key in sorted(unique)]
