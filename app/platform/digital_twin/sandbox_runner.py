from __future__ import annotations

import json
import os
import resource
import subprocess
import sys
import tempfile
from typing import Any, Dict

MAX_TIMEOUT_SECONDS = 30
MAX_CPU_SECONDS = 10
MAX_MEMORY_BYTES = 256 * 1024 * 1024
SAFE_ENV_KEYS = {"PATH", "LANG", "LC_ALL"}

_HARNESS_TEMPLATE = """
import json, sys
sys.path.insert(0, {module_dir!r})
result = {{"imported": False, "output": None, "error": None}}
try:
    import candidate_tool as _module
    result["imported"] = True
    if hasattr(_module, "run"):
        result["output"] = _module.run({test_input!r})
except Exception as exc:
    result["error"] = "%s: %s" % (type(exc).__name__, exc)
print(json.dumps(result, default=str))
"""


def execute_sandbox_tool_execution(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Run candidate tool code in an isolated, resource- and time-bounded subprocess.

    This provides process isolation, a stripped environment (no platform credentials
    or database URLs reach the subprocess), and CPU/memory/wall-clock limits. It is
    NOT full network sandboxing - no network namespace is created, so this proves a
    generated tool is syntactically and behaviorally workable, not that it is safe
    against a fully adversarial payload. Candidate code must define a top-level
    run(test_input) function to be exercised.
    """
    code = str(payload.get("code") or "")
    if not code.strip():
        return {"status": "failed", "error": "No code was provided to execute."}
    test_input = payload.get("test_input")
    expected_output = payload.get("expected_output")
    timeout_seconds = min(max(int(payload.get("timeout_seconds") or 10), 1), MAX_TIMEOUT_SECONDS)

    with tempfile.TemporaryDirectory(prefix="digital-twin-sandbox-") as workdir:
        module_path = os.path.join(workdir, "candidate_tool.py")
        harness_path = os.path.join(workdir, "harness.py")
        with open(module_path, "w") as handle:
            handle.write(code)
        with open(harness_path, "w") as handle:
            handle.write(_HARNESS_TEMPLATE.format(module_dir=workdir, test_input=test_input))

        env = {key: os.environ[key] for key in SAFE_ENV_KEYS if key in os.environ}
        try:
            completed = subprocess.run(
                [sys.executable, harness_path],
                cwd=workdir,
                env=env,
                timeout=timeout_seconds,
                capture_output=True,
                text=True,
                preexec_fn=_apply_resource_limits if hasattr(os, "fork") else None,
            )
        except subprocess.TimeoutExpired:
            return {"status": "failed", "error": "Execution timed out after %ds." % timeout_seconds}
        except Exception as exc:
            return {"status": "failed", "error": "Could not launch sandbox: %s" % type(exc).__name__}

    if completed.returncode != 0:
        return {
            "status": "failed",
            "error": "Sandbox process exited with code %d." % completed.returncode,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-4000:],
        }
    try:
        parsed = json.loads(completed.stdout.strip().splitlines()[-1]) if completed.stdout.strip() else {}
    except (json.JSONDecodeError, IndexError):
        return {"status": "failed", "error": "Sandbox output was not valid JSON.", "stdout": completed.stdout[-2000:]}

    if not parsed.get("imported"):
        return {"status": "failed", "error": parsed.get("error") or "Candidate module could not be imported."}
    if parsed.get("error"):
        return {"status": "failed", "error": parsed["error"]}
    if expected_output is not None and parsed.get("output") != expected_output:
        return {
            "status": "failed",
            "error": "Output did not match expected_output.",
            "actual_output": parsed.get("output"),
            "expected_output": expected_output,
        }
    return {"status": "completed", "output": parsed.get("output")}


def _apply_resource_limits() -> None:
    resource.setrlimit(resource.RLIMIT_CPU, (MAX_CPU_SECONDS, MAX_CPU_SECONDS))
    resource.setrlimit(resource.RLIMIT_AS, (MAX_MEMORY_BYTES, MAX_MEMORY_BYTES))
