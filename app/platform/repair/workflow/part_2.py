# Split from the legacy module to keep each Python file under 200 lines.
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional
COMMAND_TIMEOUT_SECONDS = 300

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

def write_output_file(output_path: Path, output: Dict) -> None:
    output_path.write_text(json.dumps(output, indent=2) + "\n")

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
    parser.add_argument(
        "--output",
        help="Optional path to write the workflow JSON output.",
    )

    args = parser.parse_args()

    report = build_workflow_report(dry_run=args.dry_run)

    output = compact_summary(report) if args.summary else report

    if args.output:
        output_path = Path(args.output)
        write_output_file(output_path, output)

    print(json.dumps(output, indent=2))

    if args.output:
        print(f"REPAIR WORKFLOW OUTPUT WRITTEN: {args.output}")

    if report["passed"]:
        print("SELF-HEALING REPAIR WORKFLOW PASSED")
        return

    print("SELF-HEALING REPAIR WORKFLOW FOUND ISSUES")
    raise SystemExit(1)

if __name__ == "__main__":
    main()
