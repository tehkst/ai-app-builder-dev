import json
import sys
from pathlib import Path


def load_manifest(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")

    return json.loads(path.read_text())


def artifacts_by_path(manifest: dict) -> dict:
    return {
        artifact["path"]: artifact
        for artifact in manifest.get("artifacts", [])
    }


def compare_manifests(old_manifest: dict, new_manifest: dict) -> dict:
    old_artifacts = artifacts_by_path(old_manifest)
    new_artifacts = artifacts_by_path(new_manifest)

    old_paths = set(old_artifacts)
    new_paths = set(new_artifacts)

    added_files = sorted(new_paths - old_paths)
    removed_files = sorted(old_paths - new_paths)

    modified_files = []
    unchanged_files = []

    for path in sorted(old_paths & new_paths):
        old_artifact = old_artifacts[path]
        new_artifact = new_artifacts[path]

        if old_artifact.get("sha256") != new_artifact.get("sha256"):
            modified_files.append(
                {
                    "path": path,
                    "old_sha256": old_artifact.get("sha256"),
                    "new_sha256": new_artifact.get("sha256"),
                    "old_size_bytes": old_artifact.get("size_bytes"),
                    "new_size_bytes": new_artifact.get("size_bytes"),
                }
            )
        else:
            unchanged_files.append(path)

    return {
        "passed": True,
        "old_manifest": {
            "manifest_version": old_manifest.get("manifest_version"),
            "generated_at_utc": old_manifest.get("generated_at_utc"),
            "app_id": old_manifest.get("app_id"),
            "environment": old_manifest.get("environment"),
            "artifact_count": old_manifest.get("artifact_count"),
        },
        "new_manifest": {
            "manifest_version": new_manifest.get("manifest_version"),
            "generated_at_utc": new_manifest.get("generated_at_utc"),
            "app_id": new_manifest.get("app_id"),
            "environment": new_manifest.get("environment"),
            "artifact_count": new_manifest.get("artifact_count"),
        },
        "summary": {
            "added_count": len(added_files),
            "removed_count": len(removed_files),
            "modified_count": len(modified_files),
            "unchanged_count": len(unchanged_files),
        },
        "added_files": added_files,
        "removed_files": removed_files,
        "modified_files": modified_files,
    }


def main() -> None:
    if len(sys.argv) != 3:
        print(
            json.dumps(
                {
                    "passed": False,
                    "usage": "python3 -m app.platform.artifacts.compare_manifests <old_manifest.json> <new_manifest.json>",
                },
                indent=2,
            )
        )
        raise SystemExit(1)

    old_path = Path(sys.argv[1])
    new_path = Path(sys.argv[2])

    old_manifest = load_manifest(old_path)
    new_manifest = load_manifest(new_path)

    result = compare_manifests(old_manifest, new_manifest)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
