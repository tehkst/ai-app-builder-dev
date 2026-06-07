from __future__ import annotations

import difflib
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.platform.persistence.models import PlatformGeneratedFileVersion


def _version_summary(version: PlatformGeneratedFileVersion) -> Dict[str, Any]:
    return {
        "generated_file_version_id": version.generated_file_version_id,
        "generated_file_id": version.generated_file_id,
        "workflow_run_id": version.workflow_run_id,
        "workspace_id": version.workspace_id,
        "project_id": version.project_id,
        "version_number": version.version_number,
        "path": version.path,
        "language": version.language,
        "content_hash": version.content_hash,
        "previous_content_hash": version.previous_content_hash,
        "restore_status": version.restore_status,
    }


def _line_diff(base_text: str, target_text: str) -> List[Dict[str, Any]]:
    base_lines = base_text.splitlines()
    target_lines = target_text.splitlines()

    diff_lines = list(
        difflib.ndiff(
            base_lines,
            target_lines,
        )
    )

    formatted: List[Dict[str, Any]] = []

    for line in diff_lines:
        marker = line[:2]
        content = line[2:]

        if marker == "- ":
            change_type = "removed"
        elif marker == "+ ":
            change_type = "added"
        elif marker == "  ":
            change_type = "unchanged"
        else:
            continue

        formatted.append(
            {
                "change_type": change_type,
                "content": content,
            }
        )

    return formatted


def diff_generated_file_versions(
    db: Session,
    base_version_id: str,
    target_version_id: str,
) -> Dict[str, Any]:
    base_version = (
        db.query(PlatformGeneratedFileVersion)
        .filter(
            PlatformGeneratedFileVersion.generated_file_version_id
            == base_version_id
        )
        .first()
    )
    target_version = (
        db.query(PlatformGeneratedFileVersion)
        .filter(
            PlatformGeneratedFileVersion.generated_file_version_id
            == target_version_id
        )
        .first()
    )

    if not base_version or not target_version:
        return {
            "success": True,
            "found": False,
            "base_version_found": bool(base_version),
            "target_version_found": bool(target_version),
            "base_version_id": base_version_id,
            "target_version_id": target_version_id,
            "write_mode": "db_preview_only",
            "disk_write_performed": False,
            "diff": None,
        }

    same_generated_file = (
        base_version.generated_file_id == target_version.generated_file_id
    )
    hash_changed = base_version.content_hash != target_version.content_hash
    path_changed = base_version.path != target_version.path
    language_changed = base_version.language != target_version.language
    purpose_changed = base_version.purpose != target_version.purpose
    metadata_changed = path_changed or language_changed or purpose_changed

    line_changes = _line_diff(
        base_version.content_preview or "",
        target_version.content_preview or "",
    )

    added_lines = [
        change["content"]
        for change in line_changes
        if change["change_type"] == "added"
    ]
    removed_lines = [
        change["content"]
        for change in line_changes
        if change["change_type"] == "removed"
    ]

    return {
        "success": True,
        "found": True,
        "base_version_id": base_version_id,
        "target_version_id": target_version_id,
        "same_generated_file": same_generated_file,
        "write_mode": "db_preview_only",
        "disk_write_performed": False,
        "diff": {
            "base_version": _version_summary(base_version),
            "target_version": _version_summary(target_version),
            "hash_changed": hash_changed,
            "path_changed": path_changed,
            "language_changed": language_changed,
            "purpose_changed": purpose_changed,
            "metadata_changed": metadata_changed,
            "content_changed": hash_changed,
            "added_line_count": len(added_lines),
            "removed_line_count": len(removed_lines),
            "unchanged_line_count": len(
                [
                    change
                    for change in line_changes
                    if change["change_type"] == "unchanged"
                ]
            ),
            "added_lines": added_lines,
            "removed_lines": removed_lines,
            "line_changes": line_changes,
        },
    }
