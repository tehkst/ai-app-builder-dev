"""
Data models for the Native Coding Agent.

All models are Python 3.9 compatible (no PEP 604 union syntax, no match/case).
Uses dataclasses for structured data; JSON-serializable where needed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Edit contract
# ---------------------------------------------------------------------------

@dataclass
class EditOperation:
    """A single concrete edit operation within a workspace file."""
    path: str
    operation: str          # "create" | "update" | "delete"
    strategy: str           # "ast_replace" (preferred) | "apply_patch" | "replace_file" (fallback)
    content: str            # Full file content for replace_file, unified diff for apply_patch, replacement source for ast_replace
    reason: str
    source_evidence: List[str] = field(default_factory=list)
    expected_effect: str = ""
    risk: str = "low"       # "low" | "medium" | "high"
    target_symbol: str = ""   # Symbol name for ast_replace (function/class/method name)
    target_type: str = ""     # "function" | "class" | "method" for ast_replace


@dataclass
class EditContract:
    """Validated structured edit plan from the model."""
    mission_id: str
    iteration: int
    objective: str
    edits: List[EditOperation] = field(default_factory=list)
    validation_commands: List[Dict[str, Any]] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Validation result
# ---------------------------------------------------------------------------

@dataclass
class CommandResult:
    """Result of a single command execution in the workspace."""
    argv: List[str]
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool = False
    error: Optional[str] = None


@dataclass
class ValidationOutcome:
    """Aggregated validation outcomes for one iteration."""
    iteration: int
    overall: str            # "passed" | "failed" | "blocked"
    commands: List[CommandResult] = field(default_factory=list)
    summary: str = ""


# ---------------------------------------------------------------------------
# Failure evidence
# ---------------------------------------------------------------------------

@dataclass
class FailureEvidence:
    """Normalized, redacted failure evidence for diagnosis and repair."""
    failure_id: str
    mission_id: str
    workspace_id: str
    iteration: int
    command: str            # argv joined
    exit_code: int
    category: str
    summary: str
    stdout_excerpt: str = ""
    stderr_excerpt: str = ""
    failing_tests: List[str] = field(default_factory=list)
    affected_paths: List[str] = field(default_factory=list)
    stack_frames: List[Dict[str, str]] = field(default_factory=list)
    environment_signal: Optional[str] = None
    is_code_failure: bool = True
    is_environment_failure: bool = False
    is_dependency_failure: bool = False
    is_governance_failure: bool = False
    retryable: bool = True
    confidence: str = "medium"     # "low" | "medium" | "high"

    # --- Enhanced dimensions (Condition 3) ---
    dependency_graph: List[Dict[str, Any]] = field(default_factory=list)
    # [{"source": "module_a", "target": "module_b", "relation": "imports"}]

    changed_symbols: List[Dict[str, str]] = field(default_factory=list)
    # [{"name": "MyClass", "type": "class", "file": "path/to/file.py"}]

    caller_chain: List[Dict[str, Any]] = field(default_factory=list)
    # [{"caller": "caller_func", "callee": "changed_symbol", "file": "caller_file.py", "line": 42}]

    impacted_modules: List[Dict[str, str]] = field(default_factory=list)
    # [{"module": "app.module_x", "file": "path/to/file.py", "reason": "imports changed module directly"}]

    regression_probability: str = "unknown"  # "low" | "medium" | "high" | "critical"
    regression_reason: str = ""

    architecture_violation: bool = False
    architecture_violation_detail: str = ""

    diagnosis_confidence: str = "medium"  # "low" | "medium" | "high" — our confidence in the diagnosis itself

    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def fingerprint(self) -> str:
        """Deterministic key for detecting repeated identical failures."""
        import hashlib
        key = "%s|%s|%s|%s" % (
            self.category,
            self.exit_code,
            self.stderr_excerpt[:200],
            ",".join(sorted(self.affected_paths)),
        )
        return hashlib.sha256(key.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Coding session state
# ---------------------------------------------------------------------------

@dataclass
class CodingSessionState:
    """Durable state for one coding session, persisted through evidence mechanisms."""
    session_id: str
    mission_id: str
    workflow_run_id: str
    agent_task_id: str
    workspace_id: str
    repository: str
    base_ref: str
    base_sha: str
    workspace_path: str
    status: str                     # preparing|ready|editing|validating|repairing|verified|blocked|failed|awaiting_founder_review|released
    iteration: int = 0
    edit_history: List[EditContract] = field(default_factory=list)
    validation_history: List[ValidationOutcome] = field(default_factory=list)
    failure_history: List[FailureEvidence] = field(default_factory=list)
    failure_fingerprints: List[str] = field(default_factory=list)
    changed_files: List[str] = field(default_factory=list)
    file_fingerprints: Dict[str, Dict[str, str]] = field(default_factory=dict)
    evidence_expansions: int = 0
    non_convergence_reason: Optional[str] = None
    verified_diff: Optional[VerifiedDiff] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------------------------
# Verified diff contract
# ---------------------------------------------------------------------------

@dataclass
class ChangedFile:
    """Single changed file in the verified diff."""
    path: str
    operation: str         # "create" | "update" | "delete"
    insertions: int = 0
    deletions: int = 0
    before_fingerprint: Optional[str] = None
    after_fingerprint: Optional[str] = None


@dataclass
class VerifiedDiff:
    """Final output of the Native Coding Agent — a real repository diff."""
    mission_id: str
    workflow_run_id: str
    agent_task_id: str
    workspace_id: str
    status: str             # "verified_diff_ready"
    base_ref: str
    base_sha: str
    head_tree_fingerprint: str
    iterations: int
    changed_files: List[ChangedFile] = field(default_factory=list)
    git_status: str = ""
    git_diff: str = ""
    validation: Dict[str, Any] = field(default_factory=lambda: {"overall": "passed", "commands": [], "evidence": []})
    risks: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    artifacts: List[Dict[str, str]] = field(default_factory=list)
    governance: Dict[str, bool] = field(default_factory=lambda: {
        "repository_mutated_in_workspace": True,
        "remote_repository_mutated": False,
        "branch_created_remotely": False,
        "commit_created": False,
        "push_performed": False,
        "pull_request_created": False,
    })
    next_required_action: str = "Founder review and governed repository execution approval."


# ---------------------------------------------------------------------------
# Repair evidence — exposed for audit and qualification
# ---------------------------------------------------------------------------

@dataclass
class RepairAttempt:
    """Record of a single repair attempt in the coding loop."""
    attempt_id: str
    iteration: int
    strategy_used: str           # "ast_replace" | "apply_patch" | "replace_file"
    strategy_success: bool        # Did the strategy apply successfully?
    changed_files: List[str] = field(default_factory=list)
    file_fingerprints: Dict[str, Dict[str, str]] = field(default_factory=dict)
    validation_outcome: str = ""  # "passed" | "failed"
    failure_category: str = ""
    failure_summary: str = ""
    diagnosis_confidence: str = ""
    attempted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class RepairEvidenceBundle:
    """Aggregate repair evidence for a coding session — exposed for audit."""
    session_id: str
    mission_id: str
    workspace_id: str
    total_iterations: int
    converged: bool
    attempts: List[RepairAttempt] = field(default_factory=list)
    final_diff: Optional[VerifiedDiff] = None
    non_convergence_reason: str = ""
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def summary(self) -> Dict[str, Any]:
        """Human-readable summary of repair evidence."""
        return {
            "session_id": self.session_id,
            "mission_id": self.mission_id,
            "total_iterations": self.total_iterations,
            "converged": self.converged,
            "attempts_by_strategy": self._count_by_strategy(),
            "attempts_by_outcome": self._count_by_outcome(),
            "changed_files": self._all_changed_files(),
            "non_convergence_reason": self.non_convergence_reason,
            "verified_diff_ready": self.final_diff is not None,
        }

    def _count_by_strategy(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for a in self.attempts:
            counts[a.strategy_used] = counts.get(a.strategy_used, 0) + 1
        return counts

    def _count_by_outcome(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for a in self.attempts:
            counts[a.validation_outcome] = counts.get(a.validation_outcome, 0) + 1
        return counts

    def _all_changed_files(self) -> List[str]:
        files: set = set()
        for a in self.attempts:
            files.update(a.changed_files)
        return sorted(files)
