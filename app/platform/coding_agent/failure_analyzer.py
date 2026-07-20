"""
Failure analyzer — converts test failures into bounded, structured, redacted evidence.

Classifies failures by category, identifies affected paths and stack frames,
and creates normalized FailureEvidence records for the repair planner.

Enhanced with 7 new dimensions (Condition 3):
  1. Dependency graph — which modules depend on changed files
  2. Changed symbol — which function/class was modified
  3. Caller chain — who calls the changed symbol
  4. Impacted modules — what else might break
  5. Regression probability — risk assessment
  6. Architecture violation — does this violate design constraints
  7. Confidence — how sure are we about the diagnosis
"""
from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Optional

from app.platform.coding_agent.dependency_analyzer import (
    assess_diagnosis_confidence,
    assess_impacted_modules,
    assess_regression_probability,
    build_caller_chain,
    build_dependency_graph,
    check_architecture_violations,
    detect_changed_symbols,
)
from app.platform.coding_agent.models import CommandResult, FailureEvidence


# Secret detection patterns (redacted from failure evidence)
SECRET_PATTERNS = [
    (re.compile(r"sk-[a-zA-Z0-9]{20,}", re.IGNORECASE), "sk-***"),
    (re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE), "Bearer ***"),
    (re.compile(r"ghp_[a-zA-Z0-9]{20,}"), "ghp_***"),
    (re.compile(r"DEEPSEEK_API_KEY[=:]\s*[^\s]+", re.IGNORECASE), "DEEPSEEK_API_KEY=***"),
    (re.compile(r"OPENAI_API_KEY[=:]\s*[^\s]+", re.IGNORECASE), "OPENAI_API_KEY=***"),
    (re.compile(r"GITHUB_TOKEN[=:]\s*[^\s]+", re.IGNORECASE), "GITHUB_TOKEN=***"),
    (re.compile(r"password[=:]\s*\S+", re.IGNORECASE), "password=***"),
]


def analyze_failure(
    result: CommandResult,
    mission_id: str,
    workspace_id: str,
    iteration: int,
    *,
    workspace_path: Optional[str] = None,
    architecture_constraints: Optional[List[str]] = None,
) -> FailureEvidence:
    """
    Analyze a failed command result and produce normalized failure evidence.

    Args:
        result: The failed command result.
        mission_id: Canonical mission identifier.
        workspace_id: Durable workspace identifier.
        iteration: Current iteration number.
        workspace_path: Absolute path to workspace (for dependency/symbol analysis).
        architecture_constraints: Architecture rules to check against.

    Returns:
        FailureEvidence with redacted, classified failure data including
        dependency graph, changed symbols, caller chain, impacted modules,
        regression probability, architecture violations, and diagnosis confidence.
    """
    failure_id = "FAIL-%s" % uuid.uuid4().hex[:12].upper()

    combined = result.stdout + result.stderr

    # Redact secrets
    redacted = _redact(combined)

    # Classify
    category = _classify(redacted, result)

    # Extract stack frames
    stack_frames = _extract_stack_frames(result.stderr)

    # Extract affected paths
    affected_paths = _extract_affected_paths(result.stderr, result.stdout)

    # Extract failing tests
    failing_tests = _extract_failing_tests(redacted)

    # Determine retryability
    is_code = category in {"syntax-error", "import-error", "type-error", "test-failure", "assertion-failure", "lint-failure", "build-failure"}
    is_env = category in {"dependency-unavailable", "external-service", "timeout", "workspace-lease-lost"}
    is_dep = category == "dependency-unavailable"
    is_gov = category in {"governance-denial", "repository-conflict"}

    retryable = is_code and category not in {"governance-denial"}

    # -------------------------------------------------------------------
    # Enhanced dimensions (Condition 3) — only if workspace_path provided
    # -------------------------------------------------------------------
    dependency_graph: List[Dict[str, Any]] = []
    changed_symbols: List[Dict[str, str]] = []
    caller_chain: List[Dict[str, Any]] = []
    impacted_modules: List[Dict[str, str]] = []
    regression_probability = "unknown"
    regression_reason = ""
    architecture_violation = False
    architecture_violation_detail = ""
    diagnosis_confidence = "low"

    if workspace_path and affected_paths:
        # 1. Dependency graph
        dependency_graph = build_dependency_graph(workspace_path, affected_paths)

        # 2. Changed symbols
        changed_symbols = detect_changed_symbols(workspace_path, affected_paths)

        # 3. Caller chain
        if changed_symbols:
            caller_chain = build_caller_chain(workspace_path, changed_symbols)

        # 4. Impacted modules
        impacted_modules = assess_impacted_modules(dependency_graph, affected_paths)

        # 5. Regression probability
        regression_probability, regression_reason = assess_regression_probability(
            changed_symbols, caller_chain, impacted_modules, affected_paths,
        )

        # 6. Architecture violation
        architecture_violation, architecture_violation_detail = check_architecture_violations(
            affected_paths, architecture_constraints,
        )

        # 7. Diagnosis confidence
        diagnosis_confidence = assess_diagnosis_confidence(
            stack_frames, affected_paths, category,
        )
    else:
        # Without workspace_path, use simple heuristics
        diagnosis_confidence = "high" if stack_frames else ("medium" if affected_paths else "low")
        regression_probability = "medium" if len(affected_paths) > 3 else "low"
        if regression_probability == "medium":
            regression_reason = "Multiple affected files (%d) increase regression risk." % len(affected_paths)

    # Legacy confidence field (backward compat — kept as a label around diagnosis_confidence)
    confidence = diagnosis_confidence

    return FailureEvidence(
        failure_id=failure_id,
        mission_id=mission_id,
        workspace_id=workspace_id,
        iteration=iteration,
        command=" ".join(result.argv),
        exit_code=result.exit_code,
        category=category,
        summary="Command '%s' failed with exit code %d: %s" % (
            " ".join(result.argv[:3]), result.exit_code, category,
        ),
        stdout_excerpt=result.stdout[-2000:] if result.stdout else "",
        stderr_excerpt=_redact(result.stderr)[-2000:] if result.stderr else "",
        failing_tests=failing_tests,
        affected_paths=affected_paths,
        stack_frames=stack_frames,
        environment_signal=_detect_environment_signal(redacted),
        is_code_failure=is_code,
        is_environment_failure=is_env,
        is_dependency_failure=is_dep,
        is_governance_failure=is_gov,
        retryable=retryable,
        confidence=confidence,
        # Enhanced dimensions
        dependency_graph=dependency_graph,
        changed_symbols=changed_symbols,
        caller_chain=caller_chain,
        impacted_modules=impacted_modules,
        regression_probability=regression_probability,
        regression_reason=regression_reason,
        architecture_violation=architecture_violation,
        architecture_violation_detail=architecture_violation_detail,
        diagnosis_confidence=diagnosis_confidence,
    )


def _classify(redacted_text: str, result: CommandResult) -> str:
    """Classify failure from output patterns."""
    lowered = redacted_text.lower()

    if result.timed_out:
        return "timeout"

    patterns = [
        ("syntax-error", ["syntaxerror", "invalid syntax", "unexpected eof", "expected ':'"]),
        ("import-error", ["modulenotfounderror", "importerror", "cannot import name", "no module named"]),
        ("type-error", ["typeerror", "attributeerror", "valueerror", "keyerror", "indexerror"]),
        ("assertion-failure", ["assertionerror", "assert"]),
        ("test-failure", ["failed", "failure", "test_", "tests failed", "test failed"]),
        ("lint-failure", ["lint", "flake8", "pylint", "mypy", "type check failed"]),
        ("build-failure", ["build failed", "compilation failed", "make:", "gcc", "node:"]),
        ("dependency-unavailable", ["no such file or directory", "not found", "command not found"]),
        ("governance-denial", ["unauthorized", "denied", "forbidden", "blocked", "approval"]),
        ("invalid-model-output", ["jsondecodeerror", "could not parse", "invalid json"]),
    ]

    for category, needles in patterns:
        for needle in needles:
            if needle in lowered:
                return category

    return "general-failure"


def _redact(text: str) -> str:
    """Redact secrets from failure output."""
    result = text
    for pattern, replacement in SECRET_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def _extract_stack_frames(stderr: str) -> List[Dict[str, str]]:
    """Extract Python stack frames from stderr."""
    frames: List[Dict[str, str]] = []
    # Match Python traceback lines like: File "path/to/file.py", line 42, in function_name
    pattern = re.compile(r'File\s+"([^"]+)",\s+line\s+(\d+)(?:,\s+in\s+(\w+))?')
    for match in pattern.finditer(stderr):
        frames.append({
            "file": match.group(1),
            "line": match.group(2),
            "function": match.group(3) or "",
        })
    return frames


def _extract_affected_paths(stderr: str, stdout: str) -> List[str]:
    """Extract file paths mentioned in failure output."""
    combined = stderr + stdout
    paths: set = set()

    # Python traceback paths
    for match in re.finditer(r'File\s+"([^"]+)"', combined):
        path = match.group(1)
        # Strip leading directories to get relative path
        if "/app/" in path:
            path = "app/" + path.split("/app/")[-1]
        paths.add(path)

    # Module paths
    for match in re.finditer(r'\'([a-zA-Z_][a-zA-Z0-9_.]*)\'', combined):
        module = match.group(1)
        if "." in module:
            path = module.replace(".", "/") + ".py"
            if "/app/platform/" in path or path.startswith("app/"):
                paths.add(path)

    return sorted(paths)[:20]


def _extract_failing_tests(text: str) -> List[str]:
    """Extract failing test names from output."""
    tests: List[str] = []
    # pytest patterns
    for match in re.finditer(r'(FAILED|ERROR)\s+(\S+)', text):
        test_name = match.group(2).strip()
        if test_name and "::" in test_name:
            tests.append(test_name)
    if not tests:
        # unittest patterns
        for match in re.finditer(r'ERROR:\s+(\S+)', text):
            tests.append(match.group(1).strip())
        for match in re.finditer(r'FAIL:\s+(\S+)', text):
            tests.append(match.group(1).strip())
    return tests[:50]


def _detect_environment_signal(text: str) -> Optional[str]:
    """Detect environment-level signals in failure output."""
    lowered = text.lower()
    signals = [
        ("database connection", "database-unavailable"),
        ("connect refused", "connection-refused"),
        ("no such file", "missing-file"),
        ("permission denied", "permission-denied"),
        ("out of memory", "out-of-memory"),
        ("disk full", "disk-full"),
        ("cannot allocate", "resource-exhausted"),
        ("github api", "github-api-error"),
    ]
    for pattern, signal in signals:
        if pattern in lowered:
            return signal
    return None
