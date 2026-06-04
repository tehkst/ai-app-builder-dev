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


def load_expected_artifacts_from_manifest() -> Dict[str, Dict]:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Artifact manifest not found: {MANIFEST_PATH}")

    manifest = json.loads(MANIFEST_PATH.read_text())

    return {
        artifact["path"]: artifact
        for artifact in manifest.get("artifacts", [])
    }


def detect_real_drift() -> Dict:
    expected_artifacts = load_expected_artifacts_from_manifest()
    current_artifacts = collect_current_artifacts()

    missing_files = sorted(
        path for path in expected_artifacts if path not in current_artifacts
    )

    unexpected_files = sorted(
        path for path in current_artifacts if path not in expected_artifacts
    )

    modified_files = []

    for path, expected in expected_artifacts.items():
        current = current_artifacts.get(path)

        if current is None:
            continue

        if current["sha256"] != expected["sha256"]:
            modified_files.append(
                {
                    "path": path,
                    "expected_sha256": expected["sha256"],
                    "current_sha256": current["sha256"],
                    "expected_size_bytes": expected.get("size_bytes"),
                    "current_size_bytes": current.get("size_bytes"),
                }
            )

    passed = not missing_files and not unexpected_files and not modified_files

    return {
        "passed": passed,
        "manifest_path": str(MANIFEST_PATH),
        "expected_artifact_count": len(expected_artifacts),
        "current_artifact_count": len(current_artifacts),
        "missing_files": missing_files,
        "unexpected_files": unexpected_files,
        "modified_files": modified_files,
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


def build_repair_plan(
    source: str,
    drift_result: Dict,
    simulated_failure: Optional[Dict] = None,
    simulation_mode: bool = False,
    recommendations: Optional[List[str]] = None,
) -> Dict:
    classification = classify_plan(drift_result)
    affected_files = affected_files_from_drift(drift_result)
    repair_needed = not drift_result.get("passed", False)

    return {
        "plan_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "simulation_mode": simulation_mode,
        "auto_edit_enabled": False,
        "repair_attempted": False,
        "repair_needed": repair_needed,
        "risk_level": classification["risk_level"],
        "requires_human_approval": classification["requires_human_approval"],
        "auto_fix_available": classification["auto_fix_available"],
        "classification_reason": classification["reason"],
        "simulated_failure": simulated_failure,
        "drift_result": drift_result,
        "affected_files": affected_files,
        "recommended_actions": recommendations or [],
        "approval_boundary": {
            "can_modify_real_project_files": False,
            "can_delete_files": False,
            "can_refresh_manifest": False,
            "requires_explicit_user_confirmation": True,
        },
    }


def build_repair_plan_from_simulation(simulation_report: Dict) -> Dict:
    return build_repair_plan(
        source="simulation",
        drift_result=simulation_report["drift_result"],
        simulated_failure=simulation_report.get("simulated_failure"),
        simulation_mode=simulation_report.get("simulation_mode", False),
        recommendations=simulation_report.get("recommendations", []),
    )


def build_repair_plan_from_real_drift() -> Dict:
    drift_result = detect_real_drift()

    recommendations = []

    if drift_result["modified_files"]:
        recommendations.append(
            "Modified files detected. Compare changed artifacts against trusted templates or the approved manifest."
        )

    if drift_result["unexpected_files"]:
        recommendations.append(
            "Unexpected files detected. Remove unapproved generated files or intentionally add them through the generator and manifest workflow."
        )

    if drift_result["missing_files"]:
        recommendations.append(
            "Missing files detected. Regenerate the app or restore expected artifacts from trusted templates."
        )

    if drift_result["passed"]:
        recommendations.append("No drift detected. No repair is needed.")

    return build_repair_plan(
        source="real_drift",
        drift_result=drift_result,
        simulated_failure=None,
        simulation_mode=False,
        recommendations=recommendations,
    )


def write_plan(plan: Dict, output_path: Optional[Path]) -> None:
    if output_path is None:
        return

    output_path.write_text(json.dumps(plan, indent=2) + "\n")


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
