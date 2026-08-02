from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

"""Real, checkable classification rules replacing the old two-bucket
"Canonical" (only /service.py) vs "Adapter" (everything else) authority field.
Each rule states the evidence that produced it (this codebase's existing
{"source", "kind", "fact"} node-evidence convention - see
authority_projection.py) so a classification is inspectable, not a black box.
Priority order matters: first matching rule wins, and a bad-fit label is never
forced - anything that doesn't clearly match a specific category keeps the
honest Canonical/Adapter fallback.
"""

_GATE_CALL_NAMES = {"require_founder", "authorize_governed_action"}
_GATE_PATH_MARKERS = ("governance_authorization/", "auth_boundary/")
_ROUTER_PATH_MARKERS = ("/api/routes/", "/api/")
_TRIGGER_PATH_MARKER = "/events/"
_CONNECTOR_URL_PATTERN = re.compile(r'''_URL\s*=\s*["']https?://''')
_CONNECTOR_IMPORT_PATTERN = re.compile(r'''^\s*import\s+(requests|httpx)\b|^\s*from\s+urllib\s+import\s+request\b|^\s*import\s+urllib\.request\b''', re.MULTILINE)
_ROUTER_DECORATOR_PATTERN = re.compile(r'''@\w*router\w*\.(get|post|put|delete|patch)\(''', re.IGNORECASE)
_APIROUTER_PATTERN = re.compile(r'''\bAPIRouter\s*\(''')
_UVICORN_TARGET_PATTERN = re.compile(r'''uvicorn\s+([\w\.]+):\w+''')
_ENTRY_POINT_SOURCES = ("Dockerfile", "docker-compose.yml", "scripts/start.sh")


def _discover_entry_point_modules(repo_root: Path) -> List[str]:
    modules = []
    for relative in _ENTRY_POINT_SOURCES:
        candidate = repo_root / relative
        if not candidate.is_file():
            continue
        try:
            text = candidate.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        modules.extend(_UVICORN_TARGET_PATTERN.findall(text))
    return sorted(set(modules))


_ENTRY_POINT_MODULES: Optional[List[str]] = None


def entry_point_modules(repo_root: Path) -> List[str]:
    global _ENTRY_POINT_MODULES
    if _ENTRY_POINT_MODULES is None:
        _ENTRY_POINT_MODULES = _discover_entry_point_modules(repo_root)
    return _ENTRY_POINT_MODULES


def classify_module(path: str, content: str, repo_root: Optional[Path] = None) -> Tuple[str, List[Dict[str, Any]]]:
    """Classify a Module node (repository_projection.py). Returns
    (authority_label, extra_evidence)."""
    module = path[:-3].replace("/", ".")
    if repo_root is not None and module in entry_point_modules(repo_root):
        return "Entry Point", [_evidence(path, "entry-point-invocation", "referenced by uvicorn in Dockerfile/docker-compose.yml/scripts/start.sh - never imported, so it would otherwise look orphaned")]

    if any(marker in path for marker in _GATE_PATH_MARKERS):
        return "Gate/Guard", [_evidence(path, "gate-guard-path", "lives under a governance/auth-boundary directory")]
    if any(name in content for name in _GATE_CALL_NAMES):
        called = next(name for name in _GATE_CALL_NAMES if name in content)
        return "Gate/Guard", [_evidence(path, "gate-guard-call", "calls %s(...)" % called)]

    if any(marker in path for marker in _ROUTER_PATH_MARKERS):
        return "Router/Orchestrator", [_evidence(path, "router-path", "lives under an api/routes directory")]
    if _APIROUTER_PATTERN.search(content) or _ROUTER_DECORATOR_PATTERN.search(content):
        return "Router/Orchestrator", [_evidence(path, "router-declaration", "defines APIRouter() or a @router.<verb> route")]

    if _TRIGGER_PATH_MARKER in path and Path(path).name.endswith("_publisher.py"):
        return "Trigger/Event", [_evidence(path, "event-publisher-path", "lives under events/ and matches *_publisher.py")]

    if _CONNECTOR_IMPORT_PATTERN.search(content) and _CONNECTOR_URL_PATTERN.search(content):
        return "Connector/Protocol", [_evidence(path, "external-call-pattern", "imports an HTTP client and references a *_URL = \"https://...\" constant")]

    if Path(path).name.endswith("_check.py"):
        return "Attestation/Proof", [_evidence(path, "verification-script-name", "filename matches *_check.py, this repo's one-off verification-script convention")]

    return ("Canonical" if "/service.py" in path else "Adapter"), []


def classify_function(definition: Dict[str, Any], path: str, call_names: List[str]) -> Tuple[str, List[Dict[str, Any]]]:
    """Classify a Function/Class node (symbol_projection.py). Returns
    (authority_label, extra_evidence). Only Function definitions (not Class)
    are eligible for Stub - a class body being a single statement isn't the
    same signal. call_names is the same bare-callee-name list
    project_symbols() already computes via _call_sites() for edge-building -
    passed in rather than recomputed here."""
    node = definition.get("node")

    if any(name in _GATE_CALL_NAMES for name in call_names):
        called = next(name for name in call_names if name in _GATE_CALL_NAMES)
        return "Gate/Guard", [_evidence(path, "gate-guard-call", "calls %s(...)" % called, definition.get("lineno"))]

    if definition.get("type") == "Function" and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if _ROUTER_DECORATOR_PATTERN.search(_decorator_source(node)):
            return "Router/Orchestrator", [_evidence(path, "router-declaration", "decorated with a @<router>.<verb> route", definition.get("lineno"))]
        stub_reason = _stub_reason(node)
        if stub_reason:
            return "Stub", [_evidence(path, "stub-detection", stub_reason, definition.get("lineno"))]

    return "Adapter", []


def _decorator_source(node: ast.AST) -> str:
    try:
        return "\n".join(ast.dump(decorator) for decorator in getattr(node, "decorator_list", []) or [])
    except Exception:
        return ""


def _stub_reason(node: ast.AST) -> Optional[str]:
    body = getattr(node, "body", None) or []
    if len(body) != 1 or not isinstance(body[0], ast.Return) or body[0].value is None:
        return None
    if _is_static_literal(body[0].value):
        return "returns a static literal, no conditional branches, no downstream calls"
    return None


def _is_static_literal(value: ast.AST) -> bool:
    if isinstance(value, ast.Constant):
        return True
    if isinstance(value, (ast.Dict,)):
        return all(_is_static_literal(v) for v in value.values) and all(k is None or _is_static_literal(k) for k in value.keys)
    if isinstance(value, (ast.List, ast.Tuple, ast.Set)):
        return all(_is_static_literal(element) for element in value.elts)
    return False


def _evidence(path: str, kind: str, fact: str, lineno: Optional[int] = None) -> Dict[str, Any]:
    source = "%s:%s" % (path, lineno) if lineno else path
    return {"source": source, "kind": kind, "fact": fact}
