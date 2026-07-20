"""
Native Coding Agent — main orchestrator service.

Coordinates the full edit / test / repair loop using existing platform services:
- Workspace creation and lease acquisition (execution_service)
- Repository materialization (repository_adapter)
- Model invocation (runtime/provider_router)
- Validation execution (validation engine)
- Governance authorization (governance_authorization)
- Evidence recording (operational evidence)

The CodingAgentService is a thin orchestrator. Each phase is delegated to
specialized components in the coding_agent module.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.platform.coding_agent.context_builder import build_coding_context
from app.platform.coding_agent.diff_builder import build_verified_diff
from app.platform.coding_agent.edit_executor import apply_edits
from app.platform.coding_agent.edit_planner import plan_edits
from app.platform.coding_agent.evidence import (
    record_coding_iteration,
    record_coding_session_complete,
    record_coding_session_failed,
    record_coding_session_start,
)
from app.platform.coding_agent.failure_analyzer import analyze_failure
from app.platform.coding_agent.models import (
    CodingSessionState,
    EditContract,
    FailureEvidence,
    ValidationOutcome,
    VerifiedDiff,
)
from app.platform.coding_agent.policy import (
    MAX_CODING_ITERATIONS,
    MAX_TOTAL_SESSION_RUNTIME_SECONDS,
    NATIVE_CODING_AGENT_ENABLED,
)
from app.platform.coding_agent.repair_planner import detect_non_convergence, plan_repair
from app.platform.coding_agent.session import (
    advance_session_iteration,
    create_coding_session,
    mark_blocked,
    mark_failed,
    record_failure,
    release_workspace,
    set_verified_diff,
)
from app.platform.coding_agent.validation_runner import run_validation
from app.platform.governance_authorization.service import authorize_governed_action


class CodingAgentService:
    """
    Orchestrates one mission-specific coding session.

    Lifecycle:
        prepare → edit → validate → (repair → validate)* → verify → release

    The service owns no duplicate repository or mission state. All persistence
    goes through existing evidence and workspace services.
    """

    def __init__(
        self,
        mission_id: str,
        workflow_run_id: str,
        agent_task_id: str,
        objective: str,
        target_files: List[str],
        *,
        repository: Optional[str] = None,
        base_ref: Optional[str] = None,
        owner_id: Optional[str] = None,
        engineering_manager_plan: Optional[Dict[str, Any]] = None,
        architecture_decision: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        max_iterations: Optional[int] = None,
        mission_validation_plan: Optional[List[Dict[str, Any]]] = None,
    ):
        self.mission_id = mission_id
        self.workflow_run_id = workflow_run_id
        self.agent_task_id = agent_task_id
        self.objective = objective
        self.target_files = target_files
        self.repository = repository or "tehkst/ai-app-builder-dev"
        self.base_ref = base_ref or "main"
        self.owner_id = owner_id or "NativeCodingAgent"
        self.em_plan = engineering_manager_plan or {}
        self.arch_decision = architecture_decision or {}
        self.model = model
        self.provider = provider
        self.max_iterations = max_iterations or MAX_CODING_ITERATIONS
        self.mission_validation_plan = mission_validation_plan or None

        self.session: Optional[CodingSessionState] = None
        self.repair_attempts: List[Dict[str, Any]] = []
        self.start_time: str = _now()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(self) -> Dict[str, Any]:
        """Run the full coding session and return the result."""
        if not NATIVE_CODING_AGENT_ENABLED:
            return self._build_result(
                status="blocked",
                reason="NATIVE_CODING_AGENT_ENABLED is false.",
            )

        try:
            return self._execute_loop()
        except Exception as exc:
            if self.session:
                mark_failed(self.session, "Unexpected error: %s" % exc)
                record_coding_session_failed(
                    self._session_summary(),
                    "Unexpected error: %s" % exc,
                )
            return self._build_result(
                status="failed",
                reason="Unexpected error: %s" % exc,
            )

    def _execute_loop(self) -> Dict[str, Any]:
        """The main edit/test/repair loop."""

        # --- Phase 1: Prepare workspace ---
        self.session = create_coding_session(
            mission_id=self.mission_id,
            workflow_run_id=self.workflow_run_id,
            agent_task_id=self.agent_task_id,
            repository=self.repository,
            base_ref=self.base_ref,
            owner_id=self.owner_id,
            max_iterations=self.max_iterations,
        )
        record_coding_session_start(self._session_summary())

        # --- Phase 2: Coding loop ---
        while self.session.iteration < self.max_iterations:
            # Check total session timeout
            if _elapsed_seconds(self.start_time) > MAX_TOTAL_SESSION_RUNTIME_SECONDS:
                mark_blocked(self.session, "Total session runtime exceeded.")
                break

            # --- Build context ---
            prior_failures = [
                {
                    "category": f.category,
                    "summary": f.summary,
                    "affected_paths": f.affected_paths,
                    "stderr_excerpt": f.stderr_excerpt,
                }
                for f in self.session.failure_history
            ]
            context = build_coding_context(
                mission_id=self.mission_id,
                target_files=self.target_files,
                prior_failures=prior_failures,
                architecture_constraints=self.arch_decision.get(
                    "architecture_constraints", []
                ),
                expansion_count=self.session.evidence_expansions,
            )

            # --- Phase 2a: Generate edit plan ---
            if self.session.iteration == 0:
                contract = plan_edits(
                    mission_id=self.mission_id,
                    iteration=self.session.iteration + 1,
                    objective=self.objective,
                    context=context,
                    model=self.model,
                    provider=self.provider,
                )
            else:
                # Repair mode: use the last failure
                last_failure = self.session.failure_history[-1]
                non_convergence = detect_non_convergence(self.session, last_failure)
                if non_convergence:
                    mark_blocked(self.session, non_convergence)
                    break

                contract = plan_repair(
                    session=self.session,
                    failure=last_failure,
                    model=self.model,
                    provider=self.provider,
                )

            # --- Phase 2b: Validate edit contract ---
            if not contract.edits:
                if self.session.iteration > 0:
                    mark_blocked(self.session, "Model could not produce a repair plan.")
                else:
                    mark_blocked(self.session, "Model produced an empty edit plan.")
                break

            # --- Phase 2c: Apply edits ---
            self.session.status = "editing"
            changed, fingerprints, warnings = apply_edits(
                contract=contract,
                workspace_path=self.session.workspace_path,
                changed_files=list(self.session.changed_files),
                file_fingerprints=dict(self.session.file_fingerprints),
            )

            # Track strategies used for repair evidence
            strategies_used: Dict[str, Any] = {}
            for path, fps in fingerprints.items():
                strategy = fps.get("strategy", "unknown")
                strategies_used[path] = strategy

            # Update fingerprints
            for path, fps in fingerprints.items():
                self.session.file_fingerprints[path] = fps

            # Check for blocking warnings
            blocking = [w for w in warnings if w.get("severity") == "block"]
            if blocking:
                mark_blocked(
                    self.session,
                    "Edit blocked: %s" % blocking[0].get("message", "Unknown"),
                )
                break

            # --- Phase 2d: Run validation ---
            self.session.status = "validating"

            # Get Engineering Manager validation commands
            em_validation = self.em_plan.get("validation_plan") or []

            outcome = run_validation(
                iteration=self.session.iteration + 1,
                workspace_path=self.session.workspace_path,
                mission_validation_plan=self.mission_validation_plan,
                engineering_manager_plan=em_validation,
                additional_commands=contract.validation_commands,
            )

            # --- Phase 2e: Record iteration ---
            advance_session_iteration(self.session, contract, outcome)

            record_coding_iteration(
                self._session_summary(),
                self.session.iteration,
                _contract_summary(contract),
                _outcome_summary(outcome),
            )

            # --- Phase 2f: Check validation result ---
            if outcome.overall == "passed":
                self.session.status = "verified"
                # Record successful attempt evidence (if this was a repair iteration)
                if self.session.iteration > 1:
                    import uuid
                    self.repair_attempts.append({
                        "attempt_id": "REPAIR-ATTEMPT-%s" % uuid.uuid4().hex[:12].upper(),
                        "iteration": self.session.iteration,
                        "strategy_used": next(iter(strategies_used.values()), "unknown") if strategies_used else "unknown",
                        "strategy_success": True,
                        "changed_files": list(self.session.changed_files),
                        "file_fingerprints": {
                            k: {"before": v.get("before", ""), "after": v.get("after", "")}
                            for k, v in self.session.file_fingerprints.items()
                        },
                        "validation_outcome": "passed",
                        "failure_category": "",
                        "failure_summary": "",
                        "diagnosis_confidence": "high",
                        "attempted_at": _now(),
                    })
                break

            # --- Phase 2g: Analyze failure ---
            failed_commands = [r for r in outcome.commands if r.exit_code != 0]
            if not failed_commands:
                mark_blocked(self.session, "Validation failed but no failed commands found.")
                break

            for result in failed_commands:
                failure = analyze_failure(
                    result=result,
                    mission_id=self.mission_id,
                    workspace_id=self.session.workspace_id,
                    iteration=self.session.iteration,
                    workspace_path=self.session.workspace_path,
                    architecture_constraints=self.arch_decision.get(
                        "architecture_constraints", [],
                    ),
                )
                record_failure(self.session, failure)

                # --- Record repair attempt evidence ---
                import uuid
                self.repair_attempts.append({
                    "attempt_id": "REPAIR-ATTEMPT-%s" % uuid.uuid4().hex[:12].upper(),
                    "iteration": self.session.iteration,
                    "strategy_used": strategies_used.get(
                        failure.affected_paths[0] if failure.affected_paths else "",
                        "unknown",
                    ),
                    "strategy_success": False,  # Validation failed, so strategy didn't succeed
                    "changed_files": list(self.session.changed_files),
                    "file_fingerprints": {
                        k: {"before": v.get("before", ""), "after": v.get("after", "")}
                        for k, v in self.session.file_fingerprints.items()
                    },
                    "validation_outcome": outcome.overall,
                    "failure_category": failure.category,
                    "failure_summary": failure.summary,
                    "diagnosis_confidence": failure.diagnosis_confidence,
                    "attempted_at": _now(),
                })

                # If failure is not retryable, stop
                if not failure.retryable:
                    mark_blocked(
                        self.session,
                        "Non-retryable failure: %s" % failure.summary,
                    )
                    break

            # Check for non-convergence
            if failure and not failure.retryable:
                break

            # Expand evidence if justified
            if (self.session.evidence_expansions < self.max_iterations
                    and failure
                    and failure.affected_paths):
                self.session.evidence_expansions += 1

        # --- Phase 3: Build verified diff or report failure ---
        if self.session.status == "verified":
            diff = build_verified_diff(self.session)
            set_verified_diff(self.session, diff)
            record_coding_session_complete(
                self._session_summary(),
                _diff_summary(diff),
            )
        else:
            record_coding_session_failed(
                self._session_summary(),
                self.session.non_convergence_reason or "Session did not converge.",
            )

        # --- Phase 4: Release workspace ---
        release_workspace(self.session)

        # --- Build result ---
        terminal_good = {"verified", "awaiting_founder_review", "verified_diff_ready"}
        if self.session.status in terminal_good:
            result_status = "verified_diff_ready"
        elif self.session.status == "released":
            result_status = "released"
        else:
            result_status = "blocked"

        return self._build_result(
            status=result_status,
            reason=self.session.non_convergence_reason,
        )

    # ------------------------------------------------------------------
    # Result building
    # ------------------------------------------------------------------

    def _build_result(
        self,
        status: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build the final result payload."""
        result: Dict[str, Any] = {
            "company": "AI Software Factory",
            "product": "Native Coding Agent",
            "milestone": "NCA-01",
            "status": status,
            "mission_id": self.mission_id,
            "workflow_run_id": self.workflow_run_id,
            "agent_task_id": self.agent_task_id,
        }

        if self.session:
            result["session_id"] = self.session.session_id
            result["workspace_id"] = self.session.workspace_id
            result["iterations"] = self.session.iteration
            result["workspace_status"] = self.session.status

            if self.session.verified_diff:
                diff = self.session.verified_diff
                result["verified_diff"] = {
                    "status": diff.status,
                    "base_ref": diff.base_ref,
                    "base_sha": diff.base_sha,
                    "head_tree_fingerprint": diff.head_tree_fingerprint,
                    "iterations": diff.iterations,
                    "changed_files": [
                        {"path": f.path, "operation": f.operation, "insertions": f.insertions, "deletions": f.deletions}
                        for f in diff.changed_files
                    ],
                    "validation": diff.validation,
                    "governance": diff.governance,
                    "next_required_action": diff.next_required_action,
                }

                # Include git diff (may be large, provide excerpt)
                diff_text = diff.git_diff
                if len(diff_text) > 10000:
                    result["verified_diff"]["git_diff_excerpt"] = diff_text[:10000]
                    result["verified_diff"]["git_diff_full_length"] = len(diff_text)
                else:
                    result["verified_diff"]["git_diff"] = diff_text

            if reason:
                result["reason"] = reason
                result["non_convergence_reason"] = self.session.non_convergence_reason

            if self.session.failure_history:
                result["failure_summary"] = [
                    {"category": f.category, "summary": f.summary, "retryable": f.retryable}
                    for f in self.session.failure_history
                ]

            # Expose repair evidence for audit
            if self.repair_attempts:
                result["repair_evidence"] = self.repair_attempts
                # Aggregate summary
                strategies_count: Dict[str, int] = {}
                success_count = 0
                for a in self.repair_attempts:
                    s = a.get("strategy_used", "unknown")
                    strategies_count[s] = strategies_count.get(s, 0) + 1
                    if a.get("strategy_success"):
                        success_count += 1
                result["repair_evidence_summary"] = {
                    "total_attempts": len(self.repair_attempts),
                    "successful": success_count,
                    "strategies_used": strategies_count,
                    "converged": self.session.status == "verified",
                }

        return result

    def _session_summary(self) -> Dict[str, Any]:
        """Build a summary dict for evidence recording."""
        if not self.session:
            return {
                "mission_id": self.mission_id,
                "session_id": "not-started",
                "status": "not-started",
            }
        return {
            "mission_id": self.session.mission_id,
            "session_id": self.session.session_id,
            "workspace_id": self.session.workspace_id,
            "repository": self.session.repository,
            "base_ref": self.session.base_ref,
            "iterations": self.session.iteration,
            "status": self.session.status,
        }


# ------------------------------------------------------------------
# Convenience function
# ------------------------------------------------------------------

def start_coding_session(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Entry point for starting a Native Coding Agent session from an API payload.

    Expected payload keys:
        mission_id, workflow_run_id, agent_task_id, objective, target_files,
        (optional) repository, base_ref, engineering_manager_plan,
        architecture_decision, model, provider, max_iterations,
        mission_validation_plan.

    Returns the result of executing the coding session.
    """
    service = CodingAgentService(
        mission_id=str(payload.get("mission_id") or "MISSION-UNSPECIFIED"),
        workflow_run_id=str(payload.get("workflow_run_id") or "WF-UNSPECIFIED"),
        agent_task_id=str(payload.get("agent_task_id") or "AGENT-TASK-UNSPECIFIED"),
        objective=str(payload.get("objective") or payload.get("goal") or "Implement approved changes."),
        target_files=_extract_target_files(payload),
        repository=str(payload.get("repository") or "").strip() or None,
        base_ref=str(payload.get("base_ref") or "main"),
        owner_id=str(payload.get("owner_id") or payload.get("actor") or "").strip() or None,
        engineering_manager_plan=payload.get("engineering_manager_plan") if isinstance(payload.get("engineering_manager_plan"), dict) else None,
        architecture_decision=payload.get("architecture_decision") if isinstance(payload.get("architecture_decision"), dict) else None,
        model=payload.get("model"),
        provider=payload.get("provider"),
        max_iterations=int(payload.get("max_iterations", 0)) or None,
        mission_validation_plan=payload.get("mission_validation_plan") if isinstance(payload.get("mission_validation_plan"), list) else None,
    )
    return service.execute()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _extract_target_files(payload: Dict[str, Any]) -> List[str]:
    """Extract target files from various payload shapes."""
    files = payload.get("target_files") or payload.get("files") or []
    if isinstance(files, list):
        return [str(f) for f in files if str(f).strip()]
    if isinstance(files, str):
        return [line.strip() for line in files.splitlines() if line.strip()]
    
    # Try engineering manager plan
    em = payload.get("engineering_manager_plan") if isinstance(payload.get("engineering_manager_plan"), dict) else {}
    file_plan = em.get("file_plan") or em.get("files") or []
    if isinstance(file_plan, list):
        return [str(f.get("path", f)) if isinstance(f, dict) else str(f) 
                for f in file_plan if (str(f.get("path", f)) if isinstance(f, dict) else str(f)).strip()]

    # Fallback
    return ["app/platform/server.py", "app/platform/api_contract.py"]


def _contract_summary(contract: EditContract) -> Dict[str, Any]:
    """Summarize an edit contract for evidence."""
    return {
        "mission_id": contract.mission_id,
        "iteration": contract.iteration,
        "objective": contract.objective,
        "edit_count": len(contract.edits),
        "paths": [e.path for e in contract.edits],
        "assumptions": contract.assumptions,
        "risks": contract.risks,
    }


def _outcome_summary(outcome: ValidationOutcome) -> Dict[str, Any]:
    """Summarize a validation outcome for evidence."""
    return {
        "iteration": outcome.iteration,
        "overall": outcome.overall,
        "command_count": len(outcome.commands),
        "failed_count": sum(1 for r in outcome.commands if r.exit_code != 0),
        "summary": outcome.summary,
    }


def _diff_summary(diff: VerifiedDiff) -> Dict[str, Any]:
    """Summarize a verified diff for evidence."""
    return {
        "mission_id": diff.mission_id,
        "status": diff.status,
        "base_ref": diff.base_ref,
        "iterations": diff.iterations,
        "changed_files": [
            {"path": f.path, "operation": f.operation}
            for f in diff.changed_files
        ],
        "validation": diff.validation.get("overall"),
        "governance": diff.governance,
    }


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _elapsed_seconds(start: str) -> float:
    """Calculate elapsed seconds since a start timestamp."""
    try:
        start_dt = datetime.fromisoformat(start)
        return (datetime.now(timezone.utc) - start_dt).total_seconds()
    except (ValueError, TypeError):
        return 0.0
