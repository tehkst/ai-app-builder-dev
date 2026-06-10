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
