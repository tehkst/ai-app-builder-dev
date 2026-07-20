"""
Evidence recorder — records coding session state and outcomes through existing
platform evidence mechanisms. Uses the governance authorization evidence layer
and operational evidence service for durable audit trails.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.platform.governance_authorization.evidence import record_execution_evidence
from app.platform.persistence.operational_evidence import record_operational_evidence
from app.platform.workspaces.execution_service import record_workspace_artifact


def record_coding_session_start(
    session_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Record the start of a coding session as durable evidence."""
    return record_operational_evidence(
        "coding_agent", "coding_agent_service",
        str(session_data.get("mission_id", "unknown")),
        "session_started",
        {
            "session_id": session_data.get("session_id"),
            "workspace_id": session_data.get("workspace_id"),
            "repository": session_data.get("repository"),
            "base_ref": session_data.get("base_ref"),
            "timestamp": _now(),
        },
    )


def record_coding_iteration(
    session_data: Dict[str, Any],
    iteration: int,
    edit_contract: Dict[str, Any],
    validation_outcome: Dict[str, Any],
) -> Dict[str, Any]:
    """Record one edit/test/repair iteration as evidence."""
    return record_operational_evidence(
        "coding_agent_iteration", "coding_agent_service",
        str(session_data.get("mission_id", "unknown")),
        "iteration_%d" % iteration,
        {
            "session_id": session_data.get("session_id"),
            "workspace_id": session_data.get("workspace_id"),
            "iteration": iteration,
            "edit_contract": edit_contract,
            "validation_outcome": validation_outcome,
            "timestamp": _now(),
        },
    )


def record_coding_session_complete(
    session_data: Dict[str, Any],
    verified_diff: Dict[str, Any],
) -> Dict[str, Any]:
    """Record the completion of a coding session with verified diff."""
    return record_operational_evidence(
        "coding_agent", "coding_agent_service",
        str(session_data.get("mission_id", "unknown")),
        "session_completed",
        {
            "session_id": session_data.get("session_id"),
            "workspace_id": session_data.get("workspace_id"),
            "iterations": session_data.get("iterations"),
            "status": session_data.get("status"),
            "changed_files": verified_diff.get("changed_files", []),
            "timestamp": _now(),
        },
    )


def record_coding_session_failed(
    session_data: Dict[str, Any],
    reason: str,
) -> Dict[str, Any]:
    """Record a coding session that could not converge."""
    return record_operational_evidence(
        "coding_agent", "coding_agent_service",
        str(session_data.get("mission_id", "unknown")),
        "session_failed",
        {
            "session_id": session_data.get("session_id"),
            "workspace_id": session_data.get("workspace_id"),
            "status": "failed",
            "reason": reason,
            "iterations": session_data.get("iterations"),
            "timestamp": _now(),
        },
    )


def record_execution_outcome(
    payload: Dict[str, Any],
    decision: Dict[str, Any],
    outcome: Dict[str, Any],
) -> Dict[str, Any]:
    """Record governed execution outcome via existing governance layer."""
    from app.platform.governance_authorization.service import record_governed_outcome
    return record_governed_outcome(payload, decision, outcome)


# ---------------------------------------------------------------------------
# Repair evidence
# ---------------------------------------------------------------------------

def build_repair_evidence_bundle(
    session_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build a comprehensive repair evidence bundle for a coding session.

    This exposes:
    - Every repair attempt (iteration, strategy, outcome)
    - Strategy effectiveness (which strategies worked vs. failed)
    - Convergence status
    - Final diff readiness

    Returns a JSON-serializable dict for audit and qualification reporting.
    """
    from app.platform.coding_agent.models import RepairAttempt, RepairEvidenceBundle

    attempts: List[RepairAttempt] = []
    repair_iterations = session_data.get("repair_attempts") or []

    for raw in repair_iterations:
        attempt = RepairAttempt(
            attempt_id=str(raw.get("attempt_id", "")),
            iteration=int(raw.get("iteration", 0)),
            strategy_used=str(raw.get("strategy_used", "unknown")),
            strategy_success=bool(raw.get("strategy_success", False)),
            changed_files=list(raw.get("changed_files", [])),
            file_fingerprints=dict(raw.get("file_fingerprints", {})),
            validation_outcome=str(raw.get("validation_outcome", "")),
            failure_category=str(raw.get("failure_category", "")),
            failure_summary=str(raw.get("failure_summary", "")),
            diagnosis_confidence=str(raw.get("diagnosis_confidence", "")),
            attempted_at=str(raw.get("attempted_at", _now())),
        )
        attempts.append(attempt)

    bundle = RepairEvidenceBundle(
        session_id=str(session_data.get("session_id", "")),
        mission_id=str(session_data.get("mission_id", "")),
        workspace_id=str(session_data.get("workspace_id", "")),
        total_iterations=int(session_data.get("iterations", 0)),
        converged=bool(session_data.get("status") == "verified"),
        attempts=attempts,
        non_convergence_reason=str(session_data.get("non_convergence_reason", "")),
    )

    return bundle.summary()



def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
