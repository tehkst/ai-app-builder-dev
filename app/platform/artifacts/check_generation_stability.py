import json
import subprocess
import sys
from pathlib import Path

from app.platform.artifacts.registry_report import collect_artifacts


ROOT = Path(__file__).resolve().parents[3]


def artifact_map():
    return {
        artifact["path"]: artifact
        for artifact in collect_artifacts()
    }


def run_generation(label: str) -> dict:
    result = subprocess.run(
        [sys.executable, "test_graph.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    return {
        "label": label,
        "return_code": result.returncode,
        "passed": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def compare_artifacts(first: dict, second: dict) -> dict:
    first_paths = set(first)
    second_paths = set(second)

    added_files = sorted(second_paths - first_paths)
    removed_files = sorted(first_paths - second_paths)

    modified_files = []

    for path in sorted(first_paths & second_paths):
        first_artifact = first[path]
        second_artifact = second[path]

        if first_artifact.get("sha256") != second_artifact.get("sha256"):
            modified_files.append(
                {
                    "path": path,
                    "first_sha256": first_artifact.get("sha256"),
                    "second_sha256": second_artifact.get("sha256"),
                    "first_size_bytes": first_artifact.get("size_bytes"),
                    "second_size_bytes": second_artifact.get("size_bytes"),
                }
            )

    return {
        "added_files": added_files,
        "removed_files": removed_files,
        "modified_files": modified_files,
    }


def main() -> None:
    first_run = run_generation("first_generation")
    if not first_run["passed"]:
        print(
            json.dumps(
                {
                    "passed": False,
                    "stable": False,
                    "reason": "first generation failed",
                    "first_run": first_run,
                },
                indent=2,
            )
        )
        raise SystemExit(1)

    first_artifacts = artifact_map()

    second_run = run_generation("second_generation")
    if not second_run["passed"]:
        print(
            json.dumps(
                {
                    "passed": False,
                    "stable": False,
                    "reason": "second generation failed",
                    "second_run": second_run,
                },
                indent=2,
            )
        )
        raise SystemExit(1)

    second_artifacts = artifact_map()
    comparison = compare_artifacts(first_artifacts, second_artifacts)

    stable = (
        not comparison["added_files"]
        and not comparison["removed_files"]
        and not comparison["modified_files"]
    )

    result = {
        "passed": stable,
        "stable": stable,
        "first_artifact_count": len(first_artifacts),
        "second_artifact_count": len(second_artifacts),
        "added_count": len(comparison["added_files"]),
        "removed_count": len(comparison["removed_files"]),
        "modified_count": len(comparison["modified_files"]),
        "added_files": comparison["added_files"],
        "removed_files": comparison["removed_files"],
        "modified_files": comparison["modified_files"],
    }

    print(json.dumps(result, indent=2))

    if not stable:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
