from __future__ import annotations

import re
from typing import Any, Dict, List

from app.platform.architecture_knowledge_graph.repository_projection import REPO_ROOT, _python_paths

"""Closes the "0 incoming edges doesn't mean unused" gap: repository_projection.py
and symbol_projection.py only see AST import statements, so a module dispatched
exclusively via `[sys.executable, "-m", "app.platform.X"]` (the pattern
validate_all.py uses for every one of its checks) shows zero incoming edges
despite being genuinely wired in. Recorded as a distinct "invoked_by_command"
edge type rather than conflated with "imports", so a reader can tell how
something is reached, not just that it is.
"""

_PY_MODULE_INVOCATION = re.compile(r'''["']-m["']\s*,\s*["\']([\w\.]+)["\']''')
_SHELL_MODULE_INVOCATION = re.compile(r'''python3?\s+-m\s+([\w\.]+)''')
_SHELL_SCRIPT_DIRS = ("infra/scripts", "scripts")


def project_command_invocations() -> Dict[str, Any]:
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, str]] = []
    paths = _python_paths()
    known_modules = {"module:%s" % _module_name(path) for path in paths}

    for path in paths:
        try:
            content = (REPO_ROOT / path).read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        source_id = "module:%s" % _module_name(path)
        for match in _PY_MODULE_INVOCATION.finditer(content):
            target_id = "module:%s" % match.group(1)
            if target_id in known_modules and target_id != source_id:
                edges.append(_edge(source_id, target_id, "invoked_by_command", "command-invocation (%s)" % path))

    for source_path in _command_invoking_artifacts():
        try:
            content = source_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        relative = str(source_path.relative_to(REPO_ROOT))
        real_targets = sorted({
            match for match in _SHELL_MODULE_INVOCATION.findall(content)
            if ("module:%s" % match) in known_modules
        })
        if not real_targets:
            continue
        artifact_id = "artifact:%s" % relative
        nodes.append(_artifact_node(artifact_id, relative))
        for target in real_targets:
            edges.append(_edge(artifact_id, "module:%s" % target, "invoked_by_command", "command-invocation (%s)" % relative))

    return {"nodes": nodes, "edges": _unique_edges(edges)}


def _command_invoking_artifacts():
    workflows_dir = REPO_ROOT / ".github" / "workflows"
    if workflows_dir.is_dir():
        for path in sorted(workflows_dir.glob("*.yml")):
            yield path
    for script_dir in _SHELL_SCRIPT_DIRS:
        directory = REPO_ROOT / script_dir
        if directory.is_dir():
            for path in sorted(directory.glob("*.sh")):
                yield path


def _artifact_node(artifact_id: str, relative_path: str) -> Dict[str, Any]:
    return {
        "id": artifact_id,
        "type": "Artifact",
        "name": relative_path,
        "path": relative_path,
        "authority": "Adapter",
        "lifecycle": "Active",
        "technology": {},
        "quality": {},
        "ownership": {"repository": "tehkst/ai-app-builder-dev"},
        "operational": {},
        "evidence": [{"source": relative_path, "kind": "command-invocation-source"}],
    }


def _module_name(path: str) -> str:
    return path[:-3].replace("/", ".")


def _edge(source: str, target: str, relation: str, evidence: str) -> Dict[str, str]:
    return {"source": source, "target": target, "type": relation, "evidence": evidence}


def _unique_edges(edges: List[Dict[str, str]]) -> List[Dict[str, str]]:
    unique = {(edge["source"], edge["target"], edge["type"]): edge for edge in edges}
    return [unique[key] for key in sorted(unique)]
