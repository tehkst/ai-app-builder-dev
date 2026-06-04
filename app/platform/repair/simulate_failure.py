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


def file_sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def should_skip(path: Path) -> bool:
    if "node_modules" in path.parts:
        return True

    if path.name in {".DS_Store", MANIFEST_FILENAME}:
        return True

    return False


def collect_current_artifacts(generated_app: Path) -> Dict[str, Dict]:
    artifacts = {}

    for path in sorted(generated_app.rglob("*")):
        if not path.is_file():
            continue

        if should_skip(path):
            continue

        relative_path = path.relative_to(generated_app).as_posix()

        artifacts[relative_path] = {
            "path": relative_path,
            "sha256": file_sha256(path),
            "size_bytes": path.stat().st_size,
        }

    return artifacts


def load_manifest(generated_app: Path) -> Dict[str, Dict]:
    manifest_path = generated_app / MANIFEST_FILENAME

    if not manifest_path.exists():
        raise FileNotFoundError(f"Artifact manifest not found: {manifest_path}")

    manifest = json.loads(manifest_path.read_text())

    return {
        artifact["path"]: artifact
        for artifact in manifest.get("artifacts", [])
    }


def compare_manifest_to_current(generated_app: Path) -> Dict:
    expected_artifacts = load_manifest(generated_app)
    current_artifacts = collect_current_artifacts(generated_app)

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
        "expected_artifact_count": len(expected_artifacts),
        "current_artifact_count": len(current_artifacts),
        "missing_files": missing_files,
        "unexpected_files": unexpected_files,
        "modified_files": modified_files,
    }


def apply_simulated_failure(generated_app: Path, failure_type: str) -> Dict:
    if failure_type == "modify_artifact":
        target = generated_app / "README.md"
        original_text = target.read_text()
        target.write_text(
            original_text
            + "\n\n<!-- Simulated repair-loop artifact drift. -->\n"
        )

        return {
            "failure_type": failure_type,
            "changed_file": target.relative_to(generated_app).as_posix(),
            "description": "Modified an existing generated artifact in the sandbox.",
        }

    if failure_type == "add_unexpected_file":
        target = generated_app / "SIMULATED_UNEXPECTED_FILE.txt"
        target.write_text("This file was created only inside the repair simulation sandbox.\n")

        return {
            "failure_type": failure_type,
            "changed_file": target.relative_to(generated_app).as_posix(),
            "description": "Added an unexpected generated artifact in the sandbox.",
        }

    if failure_type == "delete_artifact":
        target = generated_app / "README.md"
        target.unlink()

        return {
            "failure_type": failure_type,
            "changed_file": target.relative_to(generated_app).as_posix(),
            "description": "Deleted an expected generated artifact in the sandbox.",
        }

    raise ValueError(f"Unsupported failure type: {failure_type}")


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
