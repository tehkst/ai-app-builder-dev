# Split from the legacy module to keep each Python file under 200 lines.
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
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

def summarize_step(name: str, result: Dict) -> Dict:
    parsed = extract_json_block(result.get("stdout", ""))

    return {
        "name": name,
        "command": result["command"],
        "passed": result["passed"],
        "return_code": result["return_code"],
        "timed_out": result.get("timed_out", False),
        "parsed_output": parsed,
        "stderr": result.get("stderr") if not result["passed"] else "",
    }

def run_fast_release_gate() -> Dict:
    return summarize_step(
        "fast_release_gate",
        run_command(
            [
                sys.executable,
                "-m",
                "app.platform.release_gate",
                "--mode",
                "fast",
            ]
        ),
    )

def run_health() -> Dict:
    return summarize_step(
        "health",
        run_command(
            [
                sys.executable,
                "-m",
                "app.platform.repair.health",
            ]
        ),
    )

def run_repair_report() -> Dict:
    return summarize_step(
        "repair_diagnosis_report",
        run_command(
            [
                sys.executable,
                "-m",
                "app.platform.repair.run_repair",
                "--mode",
                "fast",
                "--write-report",
            ]
        ),
    )

def run_repair_plan() -> Dict:
    return summarize_step(
        "real_drift_repair_plan",
        run_command(
            [
                sys.executable,
                "-m",
                "app.platform.repair.plan_repair",
                "--from-drift",
                "--no-write",
            ]
        ),
    )

def run_report_index() -> Dict:
    return summarize_step(
        "latest_repair_report_index",
        run_command(
            [
                sys.executable,
                "-m",
                "app.platform.repair.list_reports",
                "--limit",
                "1",
            ]
        ),
    )
