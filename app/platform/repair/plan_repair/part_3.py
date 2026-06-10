# Split from the legacy module to keep each Python file under 200 lines.
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from app.platform.artifacts.detect_drift import (
    collect_current_artifacts,
    MANIFEST_PATH,
)
from app.platform.repair.simulate_failure import run_simulation
ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PLAN_PATH = ROOT / "repair_plan.json"
RISK_RULES = {
    "modified_files": {
        "risk_level": "medium",
        "requires_human_approval": True,
        "auto_fix_available": False,
        "reason": "Existing generated artifacts were modified and must be compared against trusted templates.",
    },
    "unexpected_files": {
        "risk_level": "low",
        "requires_human_approval": True,
        "auto_fix_available": True,
        "reason": "Unexpected generated files may be removable, but approval is required before deletion.",
    },
    "missing_files": {
        "risk_level": "high",
        "requires_human_approval": True,
        "auto_fix_available": False,
        "reason": "Expected generated artifacts are missing and may require regeneration or template restoration.",
    },
}

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a structured self-healing repair plan."
    )

    source_group = parser.add_mutually_exclusive_group()

    source_group.add_argument(
        "--from-simulation",
        choices=[
            "modify_artifact",
            "add_unexpected_file",
            "delete_artifact",
        ],
        help="Generate a repair plan from a safe simulated failure.",
    )

    source_group.add_argument(
        "--from-drift",
        action="store_true",
        help="Generate a repair plan from real generated artifact drift.",
    )

    parser.add_argument(
        "--output",
        default=str(DEFAULT_PLAN_PATH),
        help="Path to write the generated repair plan JSON.",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Print the repair plan without writing a file.",
    )

    args = parser.parse_args()

    if args.from_drift:
        plan = build_repair_plan_from_real_drift()
    else:
        failure_type = args.from_simulation or "modify_artifact"
        simulation_report = run_simulation(failure_type)
        plan = build_repair_plan_from_simulation(simulation_report)

    output_path = None if args.no_write else Path(args.output)
    write_plan(plan, output_path)

    print(json.dumps(plan, indent=2))

    if output_path:
        print(f"REPAIR PLAN WRITTEN: {output_path}")

    if plan["repair_needed"]:
        print("SELF-HEALING REPAIR PLAN CREATED")
        return

    print("NO REPAIR PLAN NEEDED")

if __name__ == "__main__":
    main()
