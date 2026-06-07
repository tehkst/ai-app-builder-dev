import json
from pathlib import Path

from app.platform.guards.filesystem_write_guard import validate_generated_file_write_path


def run_check() -> dict:
    workspace_root = str(Path("/tmp/ai-software-factory/workspaces/project-001"))

    allowed = validate_generated_file_write_path(
        workspace_root,
        "backend/app/main.py",
    )

    traversal = validate_generated_file_write_path(
        workspace_root,
        "../platform.db",
    )

    absolute = validate_generated_file_write_path(
        workspace_root,
        "/etc/passwd",
    )

    root_target = validate_generated_file_write_path(
        workspace_root,
        ".",
    )

    dangerous_root = validate_generated_file_write_path(
        "/",
        "backend/app/main.py",
    )

    windows_traversal = validate_generated_file_write_path(
        workspace_root,
        r"backend\..\platform.db",
    )

    checks = {
        "allowed_relative_path": allowed.get("allowed") is True,
        "allowed_no_disk_write": allowed.get("disk_write_performed") is False,
        "allowed_no_code_execution": allowed.get("generated_code_execution_performed") is False,
        "blocks_path_traversal": traversal.get("allowed") is False,
        "blocks_absolute_path": absolute.get("allowed") is False,
        "blocks_workspace_root_target": root_target.get("allowed") is False,
        "blocks_dangerous_workspace_root": dangerous_root.get("allowed") is False,
        "blocks_windows_style_traversal": windows_traversal.get("allowed") is False,
    }

    return {
        "check": "filesystem_write_guard_check",
        "passed": all(checks.values()),
        "checks": checks,
        "samples": {
            "allowed": allowed,
            "traversal": traversal,
            "absolute": absolute,
            "root_target": root_target,
            "dangerous_root": dangerous_root,
            "windows_traversal": windows_traversal,
        },
    }


if __name__ == "__main__":
    result = run_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["passed"] else 1)
