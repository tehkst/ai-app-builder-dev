import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from typing import Dict, List


FULL_COMMANDS = [
    {
        "name": "internal_import_guard",
        "description": "Verify internal imports reference real modules, functions, classes, constants, or variables.",
        "command": [
            sys.executable,
            "-m",
            "app.platform.guards.function_registry",
        ],
    },
    {
        "name": "generation_stability",
        "description": "Verify deterministic generation output across repeated generation runs.",
        "command": [
            sys.executable,
            "-m",
            "app.platform.artifacts.check_generation_stability",
        ],
    },
    {
        "name": "artifact_drift",
        "description": "Verify generated artifacts match the approved artifact manifest.",
        "command": [
            sys.executable,
            "-m",
            "app.platform.artifacts.detect_drift",
        ],
    },
    {
        "name": "full_validation",
        "description": "Run all platform, security, frontend, dependency, and artifact validators.",
        "command": [
            sys.executable,
            "-m",
            "app.platform.validate_all",
        ],
    },
]


FAST_COMMANDS = [
    {
        "name": "internal_import_guard",
        "description": "Verify internal imports reference real modules, functions, classes, constants, or variables.",
        "command": [
            sys.executable,
            "-m",
            "app.platform.guards.function_registry",
        ],
    },
    {
        "name": "artifact_drift",
        "description": "Verify generated artifacts match the approved artifact manifest.",
        "command": [
            sys.executable,
            "-m",
            "app.platform.artifacts.detect_drift",
        ],
    },
]


def run_command(check: Dict) -> Dict:
    print(f"Running release gate check: {check['name']}...", flush=True)

    result = subprocess.run(
        check["command"],
        capture_output=True,
        text=True,
    )

    report = {
        "name": check["name"],
        "description": check["description"],
        "command": " ".join(check["command"]),
        "passed": result.returncode == 0,
        "return_code": result.returncode,
    }

    if result.returncode != 0:
        report["stdout"] = result.stdout
        report["stderr"] = result.stderr

    return report


def build_summary(mode: str, checks: List[Dict]) -> Dict:
    passed = all(check["passed"] for check in checks)

    return {
        "passed": passed,
        "release_approved": passed and mode == "full",
        "mode": mode,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run release gate checks."
    )
    parser.add_argument(
        "--mode",
        choices=["fast", "full"],
        default="full",
        help="fast runs lightweight checks; full runs complete production approval checks.",
    )

    args = parser.parse_args()

    commands = FAST_COMMANDS if args.mode == "fast" else FULL_COMMANDS

    checks = []

    for check in commands:
        report = run_command(check)
        checks.append(report)

        if not report["passed"]:
            summary = build_summary(args.mode, checks)
            summary["failed_check"] = report

            print(json.dumps(summary, indent=2))
            print("RELEASE GATE FAILED")
            raise SystemExit(1)

    summary = build_summary(args.mode, checks)

    print(json.dumps(summary, indent=2))

    if args.mode == "fast":
        print("FAST RELEASE GATE PASSED")
        return

    print("RELEASE GATE PASSED")


if __name__ == "__main__":
    main()
