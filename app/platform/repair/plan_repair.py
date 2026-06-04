import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

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


def affected_files_from_drift(drift_result: Dict) -> List[Dict]:
    affected_files = []

    for item in drift_result.get("modified_files", []):
        affected_files.append(
            {
                "path": item["path"],
                "issue_type": "modified_file",
                "expected_sha256": item.get("expected_sha256"),
                "current_sha256": item.get("current_sha256"),
                "expected_size_bytes": item.get("expected_size_bytes"),
                "current_size_bytes": item.get("current_size_bytes"),
            }
        )

    for path in drift_result.get("unexpected_files", []):
        affected_files.append(
            {
                "path": path,
                "issue_type": "unexpected_file",
            }
        )

    for path in drift_result.get("missing_files", []):
        affected_files.append(
            {
                "path": path,
                "issue_type": "missing_file",
            }
        )

    return affected_files


def classify_plan(drift_result: Dict) -> Dict:
    if drift_result.get("missing_files"):
        return RISK_RULES["missing_files"]

    if drift_result.get("modified_files"):
        return RISK_RULES["modified_files"]

    if drift_result.get("unexpected_files"):
        return RISK_RULES["unexpected_files"]

    return {
        "risk_level": "none",
        "requires_human_approval": False,
        "auto_fix_available": False,
        "reason": "No drift detected.",
    }


def build_repair_plan_from_simulation(simulation_report: Dict) -> Dict:
    drift_result = simulation_report["drift_result"]
    classification = classify_plan(drift_result)
    affected_files = affected_files_from_drift(drift_result)

    return {
        "plan_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "simulation",
        "simulation_mode": simulation_report.get("simulation_mode", False),
        "auto_edit_enabled": False,
        "repair_attempted": False,
        "repair_needed": simulation_report.get("drift_detected", False),
        "risk_level": classification["risk_level"],
        "requires_human_approval": classification["requires_human_approval"],
        "auto_fix_available": classification["auto_fix_available"],
        "classification_reason": classification["reason"],
        "simulated_failure": simulation_report.get("simulated_failure"),
        "affected_files": affected_files,
        "recommended_actions": simulation_report.get("recommendations", []),
        "approval_boundary": {
            "can_modify_real_project_files": False,
            "can_delete_files": False,
            "can_refresh_manifest": False,
            "requires_explicit_user_confirmation": True,
        },
    }


def write_plan(plan: Dict, output_path: Optional[Path]) -> None:
    if output_path is None:
        return

    output_path.write_text(json.dumps(plan, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a structured self-healing repair plan."
    )
    parser.add_argument(
        "--from-simulation",
        choices=[
            "modify_artifact",
            "add_unexpected_file",
            "delete_artifact",
        ],
        default="modify_artifact",
        help="Generate a repair plan from a safe simulated failure.",
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

    simulation_report = run_simulation(args.from_simulation)
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
