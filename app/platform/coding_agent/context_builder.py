"""
Context builder — assembles bounded repository evidence for the coding session.

Delegates to existing Repository Intelligence for file discovery and inspection.
Never ingests the entire repository without limits.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.platform.coding_agent.policy import MAX_CONTEXT_CHARS, MAX_EVIDENCE_EXPANSIONS
from app.platform.repository_intelligence.service import inspect_repository_evidence


def build_coding_context(
    mission_id: str,
    target_files: List[str],
    *,
    prior_failures: Optional[List[Dict[str, Any]]] = None,
    architecture_constraints: Optional[List[str]] = None,
    expansion_count: int = 0,
) -> Dict[str, Any]:
    """
    Build a bounded context pack for the coding session.

    Includes:
    - Target files (from Engineering Manager file plan)
    - Neighboring files (discovered by Repository Intelligence)
    - Architecture contracts (from Architecture Agent)
    - Prior failure evidence (from previous iterations, redacted)

    Returns a dict suitable for injection into model prompts.
    """
    evidence = _gather_evidence(
        target_files=target_files,
        prior_failures=prior_failures,
        expansion_count=expansion_count,
    )

    context: Dict[str, Any] = {
        "mission_id": mission_id,
        "bounded": True,
        "evidence": evidence,
        "architecture_constraints": architecture_constraints or [],
        "max_context_chars": MAX_CONTEXT_CHARS,
    }

    return context


def _gather_evidence(
    target_files: List[str],
    prior_failures: Optional[List[Dict[str, Any]]],
    expansion_count: int,
) -> Dict[str, Any]:
    """Gather repository evidence via existing Repository Intelligence."""
    all_paths = list(dict.fromkeys(target_files))  # deduplicate preserving order

    # If prior failures suggest additional files, add them (up to expansion budget)
    if prior_failures and expansion_count < MAX_EVIDENCE_EXPANSIONS:
        extra_paths: List[str] = []
        for failure in prior_failures:
            affected = failure.get("affected_paths") or []
            extra_paths.extend(str(p) for p in affected if str(p) not in all_paths)
        all_paths.extend(extra_paths)

    # Build relevance map
    relevance: Dict[str, str] = {}
    for path in all_paths:
        relevance[path] = "Target file specified in approved implementation plan."

    result = inspect_repository_evidence(
        paths=all_paths,
        requested_by="NativeCodingAgent",
        relevance_by_path=relevance,
    )

    # Build a structured prompt-friendly evidence pack
    evidence_pack: List[Dict[str, Any]] = []
    for item in result.get("context", []):
        evidence_pack.append({
            "path": item["path"],
            "fingerprint": item.get("fingerprint"),
            "relevance": item.get("relevance"),
            "content": item.get("content"),
        })

    missing = result.get("missing", [])
    return {
        "files": evidence_pack,
        "inspected_count": result.get("inspected_count", 0),
        "missing": missing,
        "evidence_expansions_used": expansion_count,
    }
