import hashlib
import json
from pathlib import Path

from app.platform.artifacts.qualification_target import generated_app_path

GENERATED_APP = generated_app_path()
MANIFEST_FILENAME = "artifact_manifest.json"
MANIFEST_PATH = GENERATED_APP / MANIFEST_FILENAME


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def should_skip(path: Path) -> bool:
    if "node_modules" in path.parts:
        return True

    if "repair_reports" in path.parts:
        return True

    if path.name in {".DS_Store", MANIFEST_FILENAME}:
        return True

    return False


def collect_current_artifacts():
    artifacts = {}

    for path in sorted(GENERATED_APP.rglob("*")):
        if not path.is_file():
            continue

        if should_skip(path):
            continue

        relative_path = path.relative_to(GENERATED_APP).as_posix()

        artifacts[relative_path] = {
            "path": relative_path,
            "sha256": file_sha256(path),
            "size_bytes": path.stat().st_size,
        }

    return artifacts


def main() -> None:
    if not MANIFEST_PATH.exists():
        result = {
            "passed": False,
            "reason": "artifact manifest not found",
            "manifest_path": str(MANIFEST_PATH),
        }
        print(json.dumps(result, indent=2))
        raise SystemExit(1)

    manifest = json.loads(MANIFEST_PATH.read_text())

    expected_artifacts = {
        artifact["path"]: artifact
        for artifact in manifest.get("artifacts", [])
    }

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

    result = {
        "passed": passed,
        "manifest_path": str(MANIFEST_PATH),
        "expected_artifact_count": len(expected_artifacts),
        "current_artifact_count": len(current_artifacts),
        "missing_files": missing_files,
        "unexpected_files": unexpected_files,
        "modified_files": modified_files,
    }

    print(json.dumps(result, indent=2))

    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
