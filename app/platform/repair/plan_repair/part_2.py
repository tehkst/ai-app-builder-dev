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
