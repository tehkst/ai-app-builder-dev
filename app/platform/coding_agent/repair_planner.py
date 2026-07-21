"""
Repair planner — asks the model for a targeted repair using current workspace state,
exact failure evidence, previous edit history, and remaining iteration budget.

Includes convergence detection to stop on non-progress.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.platform.coding_agent.models import (
    CodingSessionState,
    EditContract,
    EditOperation,
    FailureEvidence,
    ValidationOutcome,
)
from app.platform.coding_agent.policy import MAX_IDENTICAL_FAILURES
from app.platform.runtime.service import invoke_ai


REPAIR_PLANNER_SYSTEM = """You are a precise repair engineer inside AI Software Factory.

Your task: produce a minimal, targeted repair plan that fixes specific validation failures.

STRATEGY PRIORITY (prefer minimal changes):
1. ast_replace — Replace ONLY the broken function/class/method.
   strategy="ast_replace", target_symbol="Name", target_type="function"|"class"|"method"
2. apply_patch — Unified diff showing only the fixed lines.
   strategy="apply_patch", content=unified diff with context
3. replace_file — Full file replacement (FALLBACK ONLY).

Rules:
- Only change files that are directly implicated in the failure.
- Prefer the smallest possible change — avoid full rewrites.
- Never use prose like "fix this" or "add logic" — produce concrete edits.
- If the error is environmental (not code), do NOT propose code changes.
- If you cannot determine a fix, return an empty edits list.
- Return ONLY valid JSON matching this exact structure:

{
  "edits": [
    {
      "path": "relative/path/file.py",
      "operation": "update",
      "strategy": "ast_replace",
      "content": "...corrected function/class source...",
      "target_symbol": "FunctionName",
      "target_type": "function",
      "reason": "Why this repair addresses the failure",
      "source_evidence": ["path/to/evidence"],
      "expected_effect": "What the repair fixes",
      "risk": "low"
    }
  ],
  "diagnosis": "What you believe caused the failure",
  "cannot_repair": false,
  "cannot_repair_reason": "",
  "assumptions": [],
  "risks": []
}

If you cannot repair, set cannot_repair to true and explain why.
Output only the JSON object.
"""


def plan_repair(
    session: CodingSessionState,
    failure: FailureEvidence,
    *,
    model: Optional[str] = None,
    provider: Optional[str] = None,
) -> EditContract:
    """
    Ask the model for a targeted repair using failure evidence.

    Args:
        session: Current coding session state.
        failure: The specific failure to repair.
        model: Optional model override.
        provider: Optional provider override.

    Returns:
        EditContract with repair edits, or empty edits if not repairable.
    """
    prompt = _build_repair_prompt(session, failure)

    ai_result = invoke_ai({
        "system": REPAIR_PLANNER_SYSTEM,
        "prompt": prompt,
        "model": model,
        "provider": provider,
    })

    return _parse_repair_contract(session, failure, ai_result)


def detect_non_convergence(
    session: CodingSessionState,
    current_failure: FailureEvidence,
) -> Optional[str]:
    """
    Detect if the repair loop is not converging.

    Checks:
    - Repeated identical failures (same fingerprint appearing too many times)
    - Oscillating edits (history showing back-and-forth changes)
    - No progress (same failure after repair)
    - Budget exhaustion

    Returns:
        A non-convergence reason string, or None if still converging.
    """
    # Check identical failure fingerprints
    fp = current_failure.fingerprint()
    if fp in session.failure_fingerprints:
        count = session.failure_fingerprints.count(fp)
        if count >= MAX_IDENTICAL_FAILURES:
            return "Repeated identical failure (%d occurrences): %s" % (count, current_failure.summary)

    # Check iteration budget
    if session.iteration >= session.iteration + 1:  # Can't happen due to loop guard, but safe
        return "Iteration budget exhausted at %d iterations." % session.iteration

    # Check if current failure is not code-related (environmental)
    if current_failure.is_environment_failure or current_failure.is_governance_failure:
        return "Non-code failure detected: %s (category: %s)" % (
            current_failure.summary, current_failure.category,
        )

    # Check for oscillating edits — if last two edit contracts have same files but
    # different content in opposing directions
    if len(session.edit_history) >= 4:
        recent = session.edit_history[-4:]
        paths_a = {e.path for e in recent[0].edits}
        paths_b = {e.path for e in recent[1].edits}
        paths_c = {e.path for e in recent[2].edits}
        paths_d = {e.path for e in recent[3].edits}
        if paths_a == paths_c and paths_b == paths_d and paths_a != paths_b:
            return "Oscillating edits detected: files alternate between two edit patterns without convergence."

    # Check if diffs are growing without progress
    if session.iteration > 3:
        changed_set = set(session.changed_files)
        if len(changed_set) > 8 and len(session.failure_history) >= 3:
            return "Growing diff without validation progress: %d changed files across %d failed iterations." % (
                len(changed_set), session.iteration,
            )

    return None


def _build_repair_prompt(
    session: CodingSessionState,
    failure: FailureEvidence,
) -> str:
    """Build the repair prompt with failure evidence and edit history."""
    failure_context = {
        "failure_id": failure.failure_id,
        "category": failure.category,
        "exit_code": failure.exit_code,
        "command": failure.command,
        "summary": failure.summary,
        "stderr_excerpt": failure.stderr_excerpt,
        "stdout_excerpt": failure.stdout_excerpt,
        "affected_paths": failure.affected_paths,
        "stack_frames": failure.stack_frames,
        "failing_tests": failure.failing_tests,
        "environment_signal": failure.environment_signal,
        # Enhanced dimensions for richer repair context
        "changed_symbols": failure.changed_symbols,
        "caller_chain": failure.caller_chain[:20],  # Bounded — only top 20 callers
        "impacted_modules": failure.impacted_modules,
        "dependency_graph_summary": _summarize_dependency_graph(failure.dependency_graph),
        "regression_probability": failure.regression_probability,
        "regression_reason": failure.regression_reason,
        "architecture_violation": failure.architecture_violation,
        "architecture_violation_detail": failure.architecture_violation_detail,
        "diagnosis_confidence": failure.diagnosis_confidence,
    }

    # Bounded edit history
    recent_edits: List[Dict[str, Any]] = []
    for contract in session.edit_history[-3:]:  # Last 3 iterations
        for edit in contract.edits:
            recent_edits.append({
                "path": edit.path,
                "operation": edit.operation,
                "reason": edit.reason,
                "iteration": contract.iteration,
            })

    remaining = max(0, getattr(session, "_max_iterations", 5) - session.iteration)

    return """Mission: %s
Workspace: %s
Iteration: %d
Remaining repair budget: %d iterations

=== FAILURE EVIDENCE ===
%s

=== RECENT EDIT HISTORY ===
%s

=== INSTRUCTIONS ===
Produce a minimal, targeted repair plan.
If the failure is environmental, do NOT propose code changes.
If you cannot determine a concrete fix, set cannot_repair to true.
""" % (
        session.mission_id,
        session.workspace_id,
        session.iteration,
        remaining,
        json.dumps(failure_context, sort_keys=True, indent=2),
        json.dumps(recent_edits, sort_keys=True, indent=2),
    )


def _parse_repair_contract(
    session: CodingSessionState,
    failure: FailureEvidence,
    ai_result: Dict[str, Any],
) -> EditContract:
    """Parse repair model output into an EditContract."""
    output_text = str(ai_result.get("output_text") or "").strip()

    # Strip markdown fences
    if output_text.startswith("```"):
        lines = output_text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        output_text = "\n".join(lines)

    try:
        data = json.loads(output_text)
    except json.JSONDecodeError:
        start = output_text.find("{")
        end = output_text.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(output_text[start:end + 1])
            except json.JSONDecodeError:
                data = {}
        else:
            data = {}

    # If model declares it cannot repair
    if data.get("cannot_repair") is True:
        reason = str(data.get("cannot_repair_reason", "Model could not determine a repair."))
        return EditContract(
            mission_id=session.mission_id,
            iteration=session.iteration,
            objective="Repair: %s" % failure.summary[:80],
            assumptions=["Model declared repair is not possible: %s" % reason],
            risks=["Unrepairable failure"],
        )

    diagnosis = str(data.get("diagnosis", ""))

    edits: List[EditOperation] = []
    for raw in data.get("edits", []):
        if not isinstance(raw, dict):
            continue
        edits.append(EditOperation(
            path=str(raw.get("path", "")).strip(),
            operation=str(raw.get("operation", "update")).strip(),
            strategy=str(raw.get("strategy", "replace_file")).strip(),
            content=str(raw.get("content", "")),
            reason=str(raw.get("reason", "")).strip(),
            source_evidence=[failure.failure_id] + list(raw.get("source_evidence", [])),
            expected_effect=str(raw.get("expected_effect", "")).strip(),
            risk=str(raw.get("risk", "low")).strip(),
            target_symbol=str(raw.get("target_symbol", "")).strip(),
            target_type=str(raw.get("target_type", "")).strip(),
        ))

    return EditContract(
        mission_id=session.mission_id,
        iteration=session.iteration,
        objective="Repair (%s): %s" % (failure.category, failure.summary[:60]),
        edits=edits,
        assumptions=[diagnosis] if diagnosis else [],
        risks=data.get("risks", []) if isinstance(data.get("risks"), list) else [],
    )


def _summarize_dependency_graph(graph: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Produce a bounded summary of the dependency graph for prompt context."""
    if not graph:
        return []
    # Count how many modules depend on each target
    targets: Dict[str, List[str]] = {}
    for edge in graph:
        target = edge.get("target", "")
        source = edge.get("source", "")
        if target not in targets:
            targets[target] = []
        if source not in targets[target]:
            targets[target].append(source)

    return [
        {"module": target, "dependents": sorted(sources)[:10], "dependent_count": len(sources)}
        for target, sources in sorted(targets.items())
    ][:20]
