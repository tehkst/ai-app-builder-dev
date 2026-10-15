"""Apply a Nautilus repair proposal through the existing approval-gated repair executor.

Nothing here writes files directly: the proposal's changes become ``replace_file_content``
operations for ``execute_approved_repair``, which enforces the approval gate, the sandbox
boundary and the repair plan's target list exactly as for a hand-written repair.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from app.platform.services.nautilus_repair_service.proposal import NAUTILUS_REPAIR_SAFETY_MODE, latest_nautilus_proposal
from app.platform.services.nautilus_repair_service.sandbox import within_approved_base
from app.platform.services.nautilus_repair_service.workspace_copy import sha256_text
from app.platform.services.repair_executor_service import build_replace_file_operation, execute_approved_repair

APPLICABLE_STATUSES = {"proposed"}


def _blocked(workflow_run_id: str, reason: str, proposal: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"success": True, "workflow_run_id": workflow_run_id, "safety_mode": NAUTILUS_REPAIR_SAFETY_MODE,
            "apply_status": "blocked", "block_reason": reason,
            "proposal_id": (proposal or {}).get("proposal_id"), "executor_result": None}


def _stale_paths(sandbox: Path, changes: List[Dict[str, Any]]) -> List[str]:
    """Files whose current sandbox content no longer matches what Nautilus started from."""
    stale = []
    for change in changes:
        target = sandbox / change["path"]
        if change["before_sha256"] is None:
            if target.exists():
                stale.append(change["path"])
            continue
        try:
            current = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            stale.append(change["path"])
            continue
        if sha256_text(current) != change["before_sha256"]:
            stale.append(change["path"])
    return stale


def apply_nautilus_repair_proposal(*, workflow_run_id: str, proposal_id: Optional[str] = None,
                                   requested_by: str = "platform_admin") -> Dict[str, Any]:
    proposal = latest_nautilus_proposal(workflow_run_id)
    if proposal is None:
        return _blocked(workflow_run_id, "No Nautilus repair proposal exists for this workflow run.")
    if proposal_id and proposal_id != proposal["proposal_id"]:
        return _blocked(workflow_run_id, "Only the latest Nautilus proposal can be applied; generate or review "
                                         "the latest one.", proposal)
    if proposal["proposal_status"] not in APPLICABLE_STATUSES:
        return _blocked(workflow_run_id, f"Proposal status '{proposal['proposal_status']}' cannot be applied.", proposal)
    outside = [c["path"] for c in proposal["changes"] if not c.get("within_plan_candidates")]
    if outside:
        return _blocked(workflow_run_id, "Proposal changes files outside the approved repair plan: "
                                         + ", ".join(outside), proposal)
    sandbox = Path(proposal["sandbox_root"])
    if not within_approved_base(sandbox):
        return _blocked(workflow_run_id, "Proposal sandbox is outside the approved sandbox base.", proposal)
    stale = _stale_paths(sandbox, proposal["changes"])
    if stale:
        return _blocked(workflow_run_id, "Sandbox files changed since the proposal was made: " + ", ".join(stale)
                        + ". Generate a new proposal.", proposal)

    operations = [
        build_replace_file_operation(
            target_relative_path=change["path"], replacement_content=change["replacement_content"],
            reason=f"Nautilus repair proposal {proposal['proposal_id']}",
        )
        for change in proposal["changes"]
    ]
    result = execute_approved_repair(workflow_run_id=workflow_run_id, sandbox_root=str(sandbox),
                                     operations=operations, requested_by=requested_by)
    applied = bool(result.get("applied"))
    if applied:
        proposal["proposal_status"] = "applied"
    return {"success": True, "workflow_run_id": workflow_run_id, "safety_mode": NAUTILUS_REPAIR_SAFETY_MODE,
            "apply_status": "applied" if applied else "blocked",
            "block_reason": None if applied else result.get("block_reason"),
            "proposal_id": proposal["proposal_id"], "executor_result": result}
