import json
from datetime import datetime, timezone
from pathlib import Path

from app.platform.artifacts.registry_report import (
    GENERATED_APP,
    MANIFEST_FILENAME,
    collect_artifacts,
)


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
        "manifest_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "app_id": GENERATED_APP.name,
        "environment": "local",
        "generated_app": str(GENERATED_APP),
        "manifest_path": str(manifest_path),
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }

    manifest_path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
