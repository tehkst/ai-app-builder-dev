# Split from the legacy module to keep each Python file under 200 lines.
import argparse
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict
ROOT = Path(__file__).resolve().parents[3]
SOURCE_GENERATED_APP = ROOT / "generated_apps" / "crm-saas-multifile-001"
MANIFEST_FILENAME = "artifact_manifest.json"

def recommend_for_drift(result: Dict) -> list:
    recommendations = []

    if result["modified_files"]:
        recommendations.append(
            "Modified files detected. Compare the changed artifact against the trusted template or approved manifest."
        )

    if result["unexpected_files"]:
        recommendations.append(
            "Unexpected files detected. Remove unapproved generated files or add them intentionally through the generator and manifest workflow."
        )

    if result["missing_files"]:
        recommendations.append(
            "Missing files detected. Regenerate the app or restore the expected artifact from the trusted generator."
        )

    recommendations.append(
        "Because this is simulation mode, no real project files were changed."
    )

    return recommendations

def run_simulation(failure_type: str) -> Dict:
    if not SOURCE_GENERATED_APP.exists():
        raise FileNotFoundError(f"Generated app not found: {SOURCE_GENERATED_APP}")

    with tempfile.TemporaryDirectory(prefix="repair-simulation-") as temp_dir:
        temp_root = Path(temp_dir)
        sandbox_app = temp_root / SOURCE_GENERATED_APP.name

        shutil.copytree(SOURCE_GENERATED_APP, sandbox_app)

        simulated_failure = apply_simulated_failure(
            generated_app=sandbox_app,
            failure_type=failure_type,
        )

        drift_result = compare_manifest_to_current(sandbox_app)

        return {
            "passed": True,
            "simulation_mode": True,
            "auto_edit_enabled": False,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "source_generated_app": str(SOURCE_GENERATED_APP),
            "sandbox_deleted": True,
            "simulated_failure": simulated_failure,
            "drift_detected": not drift_result["passed"],
            "drift_result": drift_result,
            "recommendations": recommend_for_drift(drift_result),
        }

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Safely simulate repair-loop failures in a temporary sandbox."
    )
    parser.add_argument(
        "--failure",
        choices=[
            "modify_artifact",
            "add_unexpected_file",
            "delete_artifact",
        ],
        default="modify_artifact",
        help="Type of simulated failure to create inside the sandbox.",
    )

    args = parser.parse_args()

    report = run_simulation(args.failure)
    print(json.dumps(report, indent=2))

    if report["drift_detected"]:
        print("SELF-HEALING REPAIR SIMULATION DETECTED DRIFT")
        return

    print("SELF-HEALING REPAIR SIMULATION PASSED WITHOUT DRIFT")

if __name__ == "__main__":
    main()
