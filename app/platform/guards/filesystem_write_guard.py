from pathlib import Path
from typing import Any, Dict, Optional


DANGEROUS_WORKSPACE_ROOTS = {
    Path("/"),
    Path("/bin"),
    Path("/boot"),
    Path("/dev"),
    Path("/etc"),
    Path("/lib"),
    Path("/lib64"),
    Path("/proc"),
    Path("/root"),
    Path("/sbin"),
    Path("/sys"),
    Path("/usr"),
    Path("/var"),
    Path("/System"),
    Path("/Library"),
    Path("/Applications"),
}


def _blocked(
    reason: str,
    *,
    workspace_root: Optional[str] = None,
    requested_path: Optional[str] = None,
    resolved_workspace_root: Optional[str] = None,
    resolved_target_path: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "allowed": False,
        "reason": reason,
        "workspace_root": workspace_root,
        "requested_path": requested_path,
        "resolved_workspace_root": resolved_workspace_root,
        "resolved_target_path": resolved_target_path,
        "guard_mode": "validate_only",
        "disk_write_performed": False,
        "generated_code_execution_performed": False,
    }


def _allowed(
    *,
    workspace_root: str,
    requested_path: str,
    resolved_workspace_root: str,
    resolved_target_path: str,
    normalized_relative_path: str,
) -> Dict[str, Any]:
    return {
        "allowed": True,
        "reason": None,
        "workspace_root": workspace_root,
        "requested_path": requested_path,
        "resolved_workspace_root": resolved_workspace_root,
        "resolved_target_path": resolved_target_path,
        "normalized_relative_path": normalized_relative_path,
        "guard_mode": "validate_only",
        "disk_write_performed": False,
        "generated_code_execution_performed": False,
    }


def _is_dangerous_workspace_root(path: Path) -> bool:
    return path in DANGEROUS_WORKSPACE_ROOTS


def validate_generated_file_write_path(
    workspace_root: str,
    relative_path: str,
    *,
    allow_absolute_path: bool = False,
) -> Dict[str, Any]:
    """
    Validate a future generated-file write target without writing anything.

    This guard intentionally performs validation only. It must not create folders,
    write files, execute generated code, or mutate generated app content.
    """

    if not workspace_root or not isinstance(workspace_root, str):
        return _blocked(
            "Workspace root is missing or invalid.",
            workspace_root=workspace_root,
            requested_path=relative_path,
        )

    if not relative_path or not isinstance(relative_path, str):
        return _blocked(
            "Requested path is missing or invalid.",
            workspace_root=workspace_root,
            requested_path=relative_path,
        )

    if "\x00" in workspace_root or "\x00" in relative_path:
        return _blocked(
            "Null byte detected in path.",
            workspace_root=workspace_root,
            requested_path=relative_path,
        )

    requested_path = relative_path.replace("\\", "/").strip()

    if not requested_path:
        return _blocked(
            "Requested path is empty after normalization.",
            workspace_root=workspace_root,
            requested_path=relative_path,
        )

    if requested_path.startswith("~"):
        return _blocked(
            "Home-directory expansion paths are not allowed.",
            workspace_root=workspace_root,
            requested_path=relative_path,
        )

    raw_target = Path(requested_path)

    if raw_target.is_absolute() and not allow_absolute_path:
        return _blocked(
            "Absolute generated-file paths are not allowed.",
            workspace_root=workspace_root,
            requested_path=relative_path,
        )

    if any(part == ".." for part in raw_target.parts):
        return _blocked(
            "Path traversal is not allowed.",
            workspace_root=workspace_root,
            requested_path=relative_path,
        )

    resolved_workspace_root = Path(workspace_root).expanduser().resolve(strict=False)

    if _is_dangerous_workspace_root(resolved_workspace_root):
        return _blocked(
            "Workspace root points to a dangerous system path.",
            workspace_root=workspace_root,
            requested_path=relative_path,
            resolved_workspace_root=str(resolved_workspace_root),
        )

    resolved_target_path = (
        raw_target.resolve(strict=False)
        if raw_target.is_absolute()
        else (resolved_workspace_root / raw_target).resolve(strict=False)
    )

    try:
        normalized_relative_path = resolved_target_path.relative_to(
            resolved_workspace_root
        )
    except ValueError:
        return _blocked(
            "Resolved target path escapes the approved workspace root.",
            workspace_root=workspace_root,
            requested_path=relative_path,
            resolved_workspace_root=str(resolved_workspace_root),
            resolved_target_path=str(resolved_target_path),
        )

    if resolved_target_path == resolved_workspace_root:
        return _blocked(
            "Target path cannot be the workspace root itself.",
            workspace_root=workspace_root,
            requested_path=relative_path,
            resolved_workspace_root=str(resolved_workspace_root),
            resolved_target_path=str(resolved_target_path),
        )

    return _allowed(
        workspace_root=workspace_root,
        requested_path=relative_path,
        resolved_workspace_root=str(resolved_workspace_root),
        resolved_target_path=str(resolved_target_path),
        normalized_relative_path=normalized_relative_path.as_posix(),
    )
