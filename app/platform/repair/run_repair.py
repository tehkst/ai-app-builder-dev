import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional


ROOT = Path(__file__).resolve().parents[3]
GENERATED_APP = ROOT / "generated_apps" / "crm-saas-multifile-001"
REPAIR_REPORT_DIR = GENERATED_APP / "repair_reports"


RELEASE_GATE_COMMAND = [
    sys.executable,
    "-m",
    "app.platform.release_gate",
]


REPAIR_RECOMMENDATIONS = {
    "generation_stability": [
        "Inspect recently changed generator or template files.",
        "Run python3 -m app.platform.artifacts.check_generation_stability directly.",
        "If generated output intentionally changed, review generated artifacts before refreshing the manifest.",
        "If generated output changed unintentionally, fix template determinism before proceeding.",
    ],
    "artifact_drift": [
        "Run python3 -m app.platform.artifacts.detect_drift directly.",
        "Inspect missing, unexpected, or modified generated files.",
        "If the drift is intentional, run python3 -m app.platform.artifacts.refresh_manifest.",
        "After refreshing the manifest, rerun drift detection and full validation.",
    ],
    "full_validation": [
        "Run python3 -m app.platform.validate_all directly.",
        "Inspect the first failed validator in the validation output.",
        "Fix the failing compatibility, security, frontend, route, generation graph, or artifact registry check.",
        "Rerun validate_all before rerunning the release gate.",
    ],
}


def run_release_gate() -> Dict:
    result = subprocess.run(
        RELEASE_GATE_COMMAND,
        capture_output=True,
        text=True,
    )

    return {
        "command": " ".join(RELEASE_GATE_COMMAND),
        "return_code": result.returncode,
        "passed": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
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


def get_failed_check(parsed_output: Optional[Dict]) -> Optional[Dict]:
    if not parsed_output:
        return None

    failed_check = parsed_output.get("failed_check")
    if failed_check:
        return failed_check

    checks = parsed_output.get("checks", [])
    for check in checks:
        if not check.get("passed", False):
            return check

    return None


def recommend_actions(failed_check: Optional[Dict]) -> list:
    if not failed_check:
        return [
            "Could not identify a specific failed release gate check.",
            "Review release gate stdout and stderr manually.",
            "Run python3 -m app.platform.release_gate directly.",
        ]

    check_name = failed_check.get("name")
    return REPAIR_RECOMMENDATIONS.get(
        check_name,
        [
            f"No specific repair playbook exists yet for check: {check_name}",
            "Review stdout and stderr manually.",
            "Add a repair playbook for this check once the failure pattern is understood.",
        ],
    )


def report_filename() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"repair_report_{timestamp}.json"


def write_report(report: Dict) -> Path:
    REPAIR_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPAIR_REPORT_DIR / report_filename()
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    return report_path


def build_report() -> Dict:
    release_gate_result = run_release_gate()
    parsed_output = extract_json_block(release_gate_result["stdout"])
    failed_check = get_failed_check(parsed_output)

    no_repair_needed = release_gate_result["passed"]

    report = {
        "passed": True,
        "repair_attempted": False,
        "repair_needed": not no_repair_needed,
        "auto_edit_enabled": False,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "release_gate": {
            "command": release_gate_result["command"],
            "passed": release_gate_result["passed"],
            "return_code": release_gate_result["return_code"],
        },
        "failed_check": failed_check,
        "recommendations": [] if no_repair_needed else recommend_actions(failed_check),
    }

    if no_repair_needed:
        report["status"] = "no repair needed"
        return report

    report["status"] = "repair needed - diagnosis only"
    report["release_gate_stdout"] = release_gate_result["stdout"]
    report["release_gate_stderr"] = release_gate_result["stderr"]

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run self-healing repair diagnosis."
    )
    parser.add_argument(
        "--write-report",
        action="store_true",
        help="Write a timestamped repair report JSON file.",
    )

    args = parser.parse_args()

    report = build_report()

    if args.write_report:
        report_path = write_report(report)
        report["report_path"] = str(report_path)

    print(json.dumps(report, indent=2))

    if args.write_report:
        print(f"REPAIR REPORT WRITTEN: {report['report_path']}")

    if not report["repair_needed"]:
        print("SELF-HEALING REPAIR CHECK PASSED")
        return

    print("SELF-HEALING REPAIR CHECK FOUND ISSUES")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
