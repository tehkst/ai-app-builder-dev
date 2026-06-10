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
