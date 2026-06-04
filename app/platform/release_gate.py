import json
import subprocess
import sys
from datetime import datetime, timezone
from typing import Dict, List


COMMANDS = [
    {
        "name": "generation_stability",
        "description": "Verify deterministic generation output across repeated generation runs.",
        "command": [sys.executable, "-m", "app.platform.artifacts.check_generation_stability"],
    },
    {
        "name": "artifact_drift",
        "description": "Verify generated artifacts match the approved artifact manifest.",
        "command": [sys.executable, "-m", "app.platform.artifacts.detect_drift"],
    },
    {
        "name": "full_validation",
        "description": "Run all platform, security, frontend, dependency, and artifact validators.",
        "command": [sys.executable, "-m", "app.platform.validate_all"],
    },
]


def run_command(name: str, description: str, command: List[str]) -> Dict:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
    )

    return {
        "name": name,
        "description": description,
        "command": " ".join(command),
        "return_code": result.returncode,
        "passed": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def build_summary(results: List[Dict], passed: bool) -> Dict:
    return {
        "passed": passed,
        "release_approved": passed,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "checks": [
            {
                "name": result["name"],
                "description": result["description"],
                "command": result["command"],
                "passed": result["passed"],
                "return_code": result["return_code"],
            }
            for result in results
        ],
    }


def main() -> None:
    results = []

    for item in COMMANDS:
        print(f"Running release gate check: {item['name']}...")

        result = run_command(
            name=item["name"],
            description=item["description"],
            command=item["command"],
        )

        results.append(result)

        if not result["passed"]:
            failure_summary = build_summary(results, passed=False)
            failure_summary["failed_check"] = {
                "name": result["name"],
                "command": result["command"],
                "return_code": result["return_code"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
            }

            print(json.dumps(failure_summary, indent=2))
            print("RELEASE GATE FAILED")
            raise SystemExit(1)

    summary = build_summary(results, passed=True)
    print(json.dumps(summary, indent=2))
    print("RELEASE GATE PASSED")


if __name__ == "__main__":
    main()
