import hashlib
import json
from pathlib import Path

from app.platform.artifacts.qualification_target import generated_app_path

GENERATED_APP = generated_app_path()


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

    result = {
        "passed": True,
        "generated_app": str(GENERATED_APP),
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
