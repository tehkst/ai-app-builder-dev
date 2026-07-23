from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[3]
CONTEXT_PATH = "app/platform/board_room/context_retriever.py"
ENGINE_PATH = "app/platform/board_room/executive_reasoning_engine.py"
CONSOLE_PATH = "app/platform/operating_console/service.py"
INTELLIGENCE_PATH = "app/platform/executive_intelligence/service.py"
CANONICAL_CONTRACT = "executive-state-v1"


def inspect_board_room_integration(repo_root: Optional[Path] = None) -> Dict[str, Any]:
    """Prove the Board Room executive-state dependency from current source evidence."""
    root = repo_root or REPO_ROOT
    checked_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    evidence_path = [
        "POST /mission-control/operating-console/chat",
        "app.platform.operating_console.service.board_room_chat",
        "app.platform.board_room.executive_reasoning_engine.ExecutiveReasoningEngine.reason",
        "app.platform.board_room.context_retriever.ContextRetriever.retrieve",
        "app.platform.executive_intelligence.service.build_executive_intelligence_briefing",
    ]
    try:
        context = _parse(root / CONTEXT_PATH)
        engine = _parse(root / ENGINE_PATH)
        console = _parse(root / CONSOLE_PATH)
        intelligence = _parse(root / INTELLIGENCE_PATH)
    except (OSError, SyntaxError) as exc:
        return _result(
            checked_at,
            evidence_path,
            status="unknown",
            confidence="none",
            contract=None,
            reason="Board Room integration source could not be inspected: %s." % type(exc).__name__,
        )

    direct_import = _imports(context, "app.platform.executive_intelligence.service", "build_executive_intelligence_briefing")
    canonical_context = any(
        _mapping_reference(context, mapping, "executive_intelligence", "build_executive_intelligence_briefing")
        for mapping in ("builders", "sources")
    )
    console_calls_engine = (
        _imports(console, "app.platform.board_room.executive_reasoning_engine", "ExecutiveReasoningEngine")
        and _constructed_method_call(console, "ExecutiveReasoningEngine", "reason")
    )
    engine_calls_context = (
        _imports(engine, "app.platform.board_room.context_retriever", "ContextRetriever")
        and _attribute_method_call(engine, "context_retriever", "retrieve")
    )
    legacy_reference = any(
        _imports(tree, "app.platform.company_intelligence.service", "build_company_intelligence_snapshot")
        or _calls(tree, "build_company_intelligence_snapshot")
        for tree in (context, console)
    )
    contract = _return_literal(intelligence, "build_executive_intelligence_briefing", "state_contract_version")
    checks = {
        "board_room_calls_executive_intelligence": bool(
            console_calls_engine and engine_calls_context and direct_import and canonical_context
        ),
        "authoritative_legacy_company_intelligence_absent": not legacy_reference,
        "canonical_contract_verified": contract == CANONICAL_CONTRACT,
    }
    if all(checks.values()):
        result = _result(checked_at, evidence_path, "pass", "high", contract, None)
        result["status"] = "consuming_executive_intelligence"
    else:
        failed = [name.replace("_", " ") for name, passed in checks.items() if not passed]
        result = _result(
            checked_at,
            evidence_path,
            status="unknown",
            confidence="none",
            contract=contract,
            reason="Integration proof failed: %s." % "; ".join(failed),
        )
    result["checks"] = checks
    return result


def _result(
    checked_at: str,
    evidence_path: List[str],
    status: str,
    confidence: str,
    contract: Optional[str],
    reason: Optional[str],
) -> Dict[str, Any]:
    return {
        "status": status,
        "source": "runtime_code_path_inspection",
        "checked_at": checked_at,
        "confidence": confidence,
        "evidence_path": evidence_path,
        "canonical_contract": contract,
        "unknown_reason": reason,
        "freshness": "checked-on-request",
    }


def _parse(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _imports(tree: ast.AST, module: str, name: str) -> bool:
    return any(
        isinstance(node, ast.ImportFrom)
        and node.module == module
        and any(alias.name == name for alias in node.names)
        for node in ast.walk(tree)
    )


def _calls(tree: ast.AST, name: str) -> bool:
    return any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == name
        for node in ast.walk(tree)
    )


def _mapping_reference(tree: ast.AST, mapping: str, key: str, call_name: str) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not any(isinstance(target, ast.Name) and target.id == mapping for target in node.targets):
            continue
        if not isinstance(node.value, ast.Dict):
            continue
        for item_key, value in zip(node.value.keys, node.value.values):
            if not isinstance(item_key, ast.Constant) or item_key.value != key:
                continue
            if isinstance(value, ast.Name):
                return value.id == call_name
            if isinstance(value, ast.Call):
                return isinstance(value.func, ast.Attribute) and value.func.attr == "_safe" and any(
                    isinstance(arg, ast.Name) and arg.id == call_name for arg in value.args
                )
    return False


def _constructed_method_call(tree: ast.AST, constructor: str, method: str) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute) or node.func.attr != method:
            continue
        owner = node.func.value
        if isinstance(owner, ast.Call) and isinstance(owner.func, ast.Name) and owner.func.id == constructor:
            return True
    return False


def _attribute_method_call(tree: ast.AST, owner_name: str, method: str) -> bool:
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == method
        and isinstance(node.func.value, ast.Attribute)
        and node.func.value.attr == owner_name
        for node in ast.walk(tree)
    )


def _return_literal(tree: ast.AST, function: str, key: str) -> Optional[str]:
    for node in tree.body:  # type: ignore[attr-defined]
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name != function:
            continue
        for child in ast.walk(node):
            if not isinstance(child, ast.Return) or not isinstance(child.value, ast.Dict):
                continue
            for item_key, value in zip(child.value.keys, child.value.values):
                if isinstance(item_key, ast.Constant) and item_key.value == key and isinstance(value, ast.Constant):
                    return value.value if isinstance(value.value, str) else None
    return None
