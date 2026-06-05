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


def build_workflow_report(dry_run: bool) -> Dict:
    steps = [
        run_fast_release_gate(),
        run_health(),
        run_repair_report(),
        run_repair_plan(),
        run_report_index(),
    ]

    passed = all(step["passed"] for step in steps)

    repair_plan_output = steps[3].get("parsed_output") or {}
    repair_needed = repair_plan_output.get("repair_needed")

    warnings = []

    if repair_needed:
        warnings.append("Repair planner detected repair is needed.")

    if dry_run:
        warnings.append("Dry run mode enabled. No repair execution was attempted.")

    return {
        "passed": passed and repair_needed is False,
        "workflow": "repair_workflow",
        "dry_run": dry_run,
        "auto_edit_real_project": False,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "step_count": len(steps),
        "steps": steps,
        "summary": {
            "fast_release_gate_passed": steps[0]["passed"],
            "health_passed": steps[1]["passed"],
            "repair_report_written": steps[2]["passed"],
            "repair_needed": repair_needed,
            "latest_report_available": bool(
                ((steps[4].get("parsed_output") or {}).get("report_count") or 0) > 0
            ),
        },
        "warnings": warnings,
    }


def compact_summary(report: Dict) -> Dict:
    latest_report_output = report["steps"][4].get("parsed_output") or {}
    latest_reports = latest_report_output.get("reports", [])
    latest_report = latest_reports[0] if latest_reports else None

    return {
        "passed": report["passed"],
        "workflow": report["workflow"],
        "dry_run": report["dry_run"],
        "auto_edit_real_project": report["auto_edit_real_project"],
        "checked_at": report["checked_at"],
        "fast_release_gate_passed": report["summary"]["fast_release_gate_passed"],
        "health_passed": report["summary"]["health_passed"],
        "repair_report_written": report["summary"]["repair_report_written"],
        "repair_needed": report["summary"]["repair_needed"],
        "latest_report_available": report["summary"]["latest_report_available"],
        "latest_report": {
            "filename": latest_report.get("filename") if latest_report else None,
            "checked_at": latest_report.get("checked_at") if latest_report else None,
            "status": latest_report.get("status") if latest_report else None,
            "repair_needed": latest_report.get("repair_needed") if latest_report else None,
        },
        "warnings": report["warnings"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the one-command self-healing repair workflow."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run checks and planning only. No repair execution is attempted.",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print compact dashboard-friendly JSON instead of the full workflow report.",
    )

    args = parser.parse_args()

    report = build_workflow_report(dry_run=args.dry_run)

    output = compact_summary(report) if args.summary else report

    print(json.dumps(output, indent=2))

    if report["passed"]:
        print("SELF-HEALING REPAIR WORKFLOW PASSED")
        return

    print("SELF-HEALING REPAIR WORKFLOW FOUND ISSUES")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
