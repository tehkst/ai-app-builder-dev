# Split from the legacy module to keep each Python file under 200 lines.
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from typing import Dict, Optional
COMMAND_TIMEOUT_SECONDS = 300

def run_command(command: list) -> Dict:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )

        return {
            "command": " ".join(command),
            "return_code": result.returncode,
            "passed": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as error:
        return {
            "command": " ".join(command),
            "return_code": None,
            "passed": False,
            "stdout": error.stdout or "",
            "stderr": error.stderr or "",
            "timed_out": True,
            "timeout_seconds": COMMAND_TIMEOUT_SECONDS,
        }

def extract_json_block(stdout: str) -> Optional[Dict]:
    start = stdout.find("{")
    end = stdout.rfind("}")

    if start == -1 or end == -1 or end <= start:
        return None

    try:
        return json.loads(stdout[start : end + 1])
    except json.JSONDecodeError:
        return None

def summarize_release_gate() -> Dict:
    return {
        "passed": None,
        "return_code": None,
        "release_approved": None,
        "failed_check": None,
        "check_count": None,
        "skipped": True,
        "reason": (
            "Full release gate is intentionally not run inside health summary "
            "because it can be slow. Run python3 -m app.platform.release_gate "
            "for production approval."
        ),
    }

def summarize_drift() -> Dict:
    result = run_command(
        [
            sys.executable,
            "-m",
            "app.platform.artifacts.detect_drift",
        ]
    )

    parsed = extract_json_block(result["stdout"]) or {}

    return {
        "passed": result["passed"],
        "return_code": result["return_code"],
        "timed_out": result.get("timed_out", False),
        "expected_artifact_count": parsed.get("expected_artifact_count"),
        "current_artifact_count": parsed.get("current_artifact_count"),
        "missing_count": len(parsed.get("missing_files", [])),
        "unexpected_count": len(parsed.get("unexpected_files", [])),
        "modified_count": len(parsed.get("modified_files", [])),
    }

def summarize_latest_report() -> Dict:
    result = run_command(
        [
            sys.executable,
            "-m",
            "app.platform.repair.list_reports",
            "--limit",
            "1",
        ]
    )

    parsed = extract_json_block(result["stdout"]) or {}
    reports = parsed.get("reports", [])
    latest = reports[0] if reports else None

    return {
        "passed": result["passed"],
        "return_code": result["return_code"],
        "timed_out": result.get("timed_out", False),
        "report_count": parsed.get("report_count", 0),
        "latest_report": latest,
    }

def summarize_planner() -> Dict:
    result = run_command(
        [
            sys.executable,
            "-m",
            "app.platform.repair.plan_repair",
            "--from-drift",
            "--no-write",
        ]
    )

    parsed = extract_json_block(result["stdout"]) or {}

    return {
        "passed": result["passed"],
        "return_code": result["return_code"],
        "timed_out": result.get("timed_out", False),
        "repair_needed": parsed.get("repair_needed"),
        "risk_level": parsed.get("risk_level"),
        "auto_fix_available": parsed.get("auto_fix_available"),
        "affected_file_count": len(parsed.get("affected_files", [])),
    }
