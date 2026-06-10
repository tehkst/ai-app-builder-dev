# Split from the legacy module to keep each Python file under 200 lines.
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from typing import Dict, Optional
COMMAND_TIMEOUT_SECONDS = 300

def build_health_summary() -> Dict:
    release_gate = summarize_release_gate()
    drift = summarize_drift()
    latest_report = summarize_latest_report()
    planner = summarize_planner()

    healthy = (
        drift["passed"]
        and planner["passed"]
        and planner["repair_needed"] is False
    )

    warnings = []

    if release_gate.get("skipped"):
        warnings.append(
            "Full release gate was not run by health summary. "
            "Run python3 -m app.platform.release_gate for production approval."
        )
    elif not release_gate["passed"]:
        warnings.append("Release gate failed.")

    if latest_report["report_count"] == 0:
        warnings.append("No repair reports found yet.")

    if planner["repair_needed"]:
        warnings.append("Repair planner detected repair is needed.")

    if not drift["passed"]:
        warnings.append("Artifact drift detected.")

    return {
        "passed": healthy,
        "healthy": healthy,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "release_gate_passed": release_gate["passed"],
            "release_approved": release_gate["release_approved"],
            "release_gate_skipped": release_gate.get("skipped", False),
            "artifact_drift_passed": drift["passed"],
            "planner_repair_needed": planner["repair_needed"],
            "latest_report_available": latest_report["report_count"] > 0,
        },
        "release_gate": release_gate,
        "artifact_drift": drift,
        "repair_planner": planner,
        "latest_repair_report": latest_report,
        "warnings": warnings,
    }

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Show self-healing repair system health summary."
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Print a short human-readable summary after JSON output.",
    )

    args = parser.parse_args()

    health = build_health_summary()

    print(json.dumps(health, indent=2))

    if args.pretty:
        status = "HEALTHY" if health["healthy"] else "NEEDS ATTENTION"
        print(f"AI SOFTWARE FACTORY HEALTH: {status}")

    if health["healthy"]:
        print("AI SOFTWARE FACTORY HEALTH CHECK PASSED")
        return

    print("AI SOFTWARE FACTORY HEALTH CHECK FOUND ISSUES")
    raise SystemExit(1)

if __name__ == "__main__":
    main()
