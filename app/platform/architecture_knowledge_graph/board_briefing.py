from __future__ import annotations

import re
from typing import Any, Dict, List

from app.platform.architecture_knowledge_graph.projection import build_graph

MAX_MODULES = 12
MAX_EDGES_PER_MODULE = 15

_STOP_WORDS = {
    "about", "after", "again", "also", "because", "before", "being", "could",
    "does", "from", "have", "how", "into", "jarvis", "more", "please", "should",
    "that", "their", "there", "these", "this", "through", "what", "with",
    "would", "your", "connect", "depends", "depend", "module",
    # Structural terms that appear in nearly every module's dotted name or path
    # in this codebase (app/platform/...) - without excluding them, any message
    # mentioning "app" or "platform" would score every module as relevant.
    "app", "platform", "py",
}


def build_architecture_graph_briefing(founder_request: str) -> Dict[str, Any]:
    """Bounded, real-evidence summary of the AST-based architecture graph for Jarvis.

    Never returns the full graph (it can have 1000+ nodes) - selects a small set
    of modules either by keyword relevance to the founder's actual message, or,
    when nothing matches, by real connectivity (most inbound+outbound edges) so
    the fallback is still a genuine signal rather than an arbitrary slice.
    """
    graph = build_graph()
    modules = [node for node in graph["nodes"] if node["type"] == "Module"]
    by_id = {node["id"]: node for node in graph["nodes"]}
    edges = graph["edges"]

    tokens = _tokens(founder_request)
    scored = [(module, _relevance_score(module, tokens)) for module in modules] if tokens else []
    matched = [module for module, score in scored if score > 0]
    if matched:
        matched.sort(key=lambda module: _relevance_score(module, tokens), reverse=True)
        selected = matched[:MAX_MODULES]
        selection_basis = "founder-message-keyword-match"
    else:
        selected = sorted(
            modules,
            key=lambda module: module["relationships"]["inbound"] + module["relationships"]["outbound"],
            reverse=True,
        )[:MAX_MODULES]
        selection_basis = "most-connected-modules-no-keyword-match"

    return {
        "status": "ready",
        "mode": "ast-import-graph",
        "evidence": "Python-AST-derived module dependency graph (architecture_knowledge_graph)",
        "source_revision": graph["source_revision"],
        "total_modules_in_graph": len(modules),
        "total_edges_in_graph": len(edges),
        "bounded": True,
        "shown_module_count": len(selected),
        "selection_basis": selection_basis,
        "modules": [_module_briefing(module, edges, by_id) for module in selected],
    }


def _module_briefing(module: Dict[str, Any], edges: List[Dict[str, str]], by_id: Dict[str, Any]) -> Dict[str, Any]:
    imports = sorted(
        by_id[edge["target"]]["name"]
        for edge in edges
        if edge["source"] == module["id"] and edge["type"] == "imports" and edge["target"] in by_id
    )[:MAX_EDGES_PER_MODULE]
    imported_by = sorted(
        by_id[edge["source"]]["name"]
        for edge in edges
        if edge["target"] == module["id"] and edge["type"] == "imports" and edge["source"] in by_id
    )[:MAX_EDGES_PER_MODULE]
    quality = module.get("quality") or {}
    return {
        "module": module["name"],
        "path": module.get("path"),
        "authority": module.get("authority"),
        "line_rule": quality.get("line_rule"),
        "loc": quality.get("loc"),
        "imports": imports,
        "imported_by": imported_by,
    }


_FILE_EXTENSIONS = (".py", ".pyc")


def _tokens(text: str) -> set[str]:
    raw = {word for word in re.findall(r"[a-z][a-z_.-]{2,}", text.lower()) if word not in _STOP_WORDS}
    stripped = set()
    for word in raw:
        for extension in _FILE_EXTENSIONS:
            if word.endswith(extension):
                word = word[: -len(extension)]
        stripped.add(word)
    return stripped


def _relevance_score(module: Dict[str, Any], tokens: set[str]) -> int:
    # Split on "." and "/" (dotted-name and path separators) for whole-segment
    # matches, PLUS "_" for compound-identifier sub-words - both still exact
    # token-set membership, never raw substring containment, so this doesn't
    # reintroduce the "rest" matching inside "restore" false positive a whole-
    # segment-only version was built to avoid. The "_" split is necessary: a
    # real regression found a founder asking about "the knowledge graph"
    # matched app/platform/knowledge/ (an unrelated package, Knowledge Vault)
    # while architecture_knowledge_graph/ itself scored zero, because splitting
    # only on "." and "/" treats "architecture_knowledge_graph" as one
    # indivisible segment that can never match the founder's separate words
    # "knowledge" and "graph" - a two-word phrase can never match a compound,
    # underscore-joined directory name without this.
    name_parts = set(re.split(r"[._]", str(module.get("name") or "").lower()))
    path_parts = set(re.split(r"[./_]", str(module.get("path") or "").lower()))
    parts = name_parts | path_parts
    return sum(1 for token in tokens if token in parts)
