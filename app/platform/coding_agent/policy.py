"""
Coding Agent policy configuration.

All safety limits, iteration budgets, and validation defaults live here.
These are configurable via environment variables but have safe production defaults.
"""
from __future__ import annotations

import os
from typing import List


def _int_env(key: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(key, str(default))))
    except (ValueError, TypeError):
        return default


def _bool_env(key: str, default: bool) -> bool:
    value = os.getenv(key, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "y"}


# ---------------------------------------------------------------------------
# Feature flag
# ---------------------------------------------------------------------------

NATIVE_CODING_AGENT_ENABLED: bool = _bool_env("NATIVE_CODING_AGENT_ENABLED", False)

# ---------------------------------------------------------------------------
# Iteration budget
# ---------------------------------------------------------------------------

MAX_CODING_ITERATIONS: int = _int_env("NATIVE_CODING_MAX_ITERATIONS", 5)
MAX_EVIDENCE_EXPANSIONS: int = _int_env("NATIVE_CODING_MAX_EVIDENCE_EXPANSIONS", 3)
MAX_CHANGED_FILES_HARD_LIMIT: int = _int_env("NATIVE_CODING_MAX_CHANGED_FILES", 30)

# ---------------------------------------------------------------------------
# Command execution
# ---------------------------------------------------------------------------

MAX_COMMAND_RUNTIME_SECONDS: int = _int_env("NATIVE_CODING_MAX_COMMAND_RUNTIME", 900)
MAX_TOTAL_SESSION_RUNTIME_SECONDS: int = _int_env("NATIVE_CODING_MAX_SESSION_RUNTIME", 3600)
MAX_STDOUT_CHARS: int = _int_env("NATIVE_CODING_MAX_STDOUT_CHARS", 20000)
MAX_STDERR_CHARS: int = _int_env("NATIVE_CODING_MAX_STDERR_CHARS", 10000)
ALLOW_NETWORK_IN_COMMANDS: bool = _bool_env("NATIVE_CODING_ALLOW_NETWORK", False)

# ---------------------------------------------------------------------------
# Edit safety
# ---------------------------------------------------------------------------

MAX_FILE_SIZE_BYTES: int = _int_env("NATIVE_CODING_MAX_FILE_SIZE", 500_000)
MAX_CONTEXT_CHARS: int = _int_env("NATIVE_CODING_MAX_CONTEXT_CHARS", 180_000)
MAX_EDIT_FINGERPRINT_CHARS: int = _int_env("NATIVE_CODING_MAX_FINGERPRINT_CHARS", 1000)

# ---------------------------------------------------------------------------
# Repair
# ---------------------------------------------------------------------------

MAX_IDENTICAL_FAILURES: int = _int_env("NATIVE_CODING_MAX_IDENTICAL_FAILURES", 2)

# ---------------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------------

DEFAULT_WORKSPACE_LEASE_SECONDS: int = _int_env("NATIVE_CODING_WORKSPACE_LEASE_SECONDS", 600)
DEFAULT_RETENTION_HOURS: int = _int_env("NATIVE_CODING_RETENTION_HOURS", 24)

# ---------------------------------------------------------------------------
# Default validation commands (fallback when none are specified)
# ---------------------------------------------------------------------------

DEFAULT_SYNTAX_CHECK: List[str] = ["python3", "-m", "compileall", "app"]
DEFAULT_GIT_DIFF_CHECK: List[str] = ["git", "diff", "--check"]

# ---------------------------------------------------------------------------
# Unsafe shell metacharacters that are rejected in command argv
# ---------------------------------------------------------------------------

UNSAFE_METACHARS: str = ";&|`$(){}[]!<>\\\"'"

# ---------------------------------------------------------------------------
# Paths excluded from editing
# ---------------------------------------------------------------------------

EXCLUDED_PATH_PREFIXES: List[str] = [
    ".git",
    "__pycache__",
    ".env",
    "credentials",
    "secrets",
]

# ---------------------------------------------------------------------------
# Python 3.9 compatible validation
# ---------------------------------------------------------------------------

PYTHON_BINARY: str = os.getenv("NATIVE_CODING_PYTHON_BINARY", "python3")
