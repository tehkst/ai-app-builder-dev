import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
GENERATED_APP = ROOT / "generated_apps" / "crm-saas-multifile-001"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


MANIFEST_FILENAME = "artifact_manifest.json"


def collect_artifacts():
    artifacts = []

    for path in sorted(GENERATED_APP.rglob("*")):
        if not path.is_file():
            continue

        if "node_modules" in path.parts:
            continue

        if path.name in {".DS_Store", MANIFEST_FILENAME}:
            continue

        relative_path = path.relative_to(GENERATED_APP).as_posix()

        artifacts.append(
            {
                "path": relative_path,
                "sha256": file_sha256(path),
                "size_bytes": path.stat().st_size,
            }
        )

    return artifacts


def main() -> None:
    if not GENERATED_APP.exists():
        result = {
            "passed": False,
            "reason": "generated app directory not found",
            "generated_app": str(GENERATED_APP),
        }
        print(json.dumps(result, indent=2))
        raise SystemExit(1)

    artifacts = collect_artifacts()

    manifest_path = GENERATED_APP / MANIFEST_FILENAME

    result = {
        "passed": True,
        "generated_app": str(GENERATED_APP),
        "manifest_path": str(manifest_path),
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }

    manifest_path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
