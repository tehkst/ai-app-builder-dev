from __future__ import annotations

from typing import Any, Dict

from sqlalchemy.orm import Session

from app.platform.services.generated_file_version_restore_plan_service import (
    create_generated_file_version_restore_plan,
)


def simulate_generated_file_version_restore(
    db: Session,
    target_version_id: str,
) -> Dict[str, Any]:
    plan = create_generated_file_version_restore_plan(
        db,
        target_version_id=target_version_id,
    )

    if not plan.get("found"):
        return {
            "success": True,
            "found": False,
            "target_version_id": target_version_id,
            "simulation_mode": "dry_run_only",
            "write_mode": "db_preview_only",
            "restore_execution_performed": False,
            "db_content_mutation_performed": False,
            "disk_write_performed": False,
            "generated_code_execution_performed": False,
            "simulation": None,
            "restore_plan": plan,
        }

    restore_plan = plan.get("restore_plan") or {}
    target_version = restore_plan.get("target_version") or {}
    current_file = restore_plan.get("current_file") or {}

    current_content = current_file.get("content_preview") or ""
    target_content = (
        target_version.get("content_snapshot")
        or target_version.get("content_preview")
        or target_version.get("content")
        or ""
    )

    content_would_change = current_content != target_content
    current_hash = current_file.get("content_hash")
    target_hash = target_version.get("content_hash")
    hash_would_change = current_hash != target_hash

    current_lines = current_content.splitlines()
    target_lines = target_content.splitlines()

    added_line_count = max(len(target_lines) - len(current_lines), 0)
    removed_line_count = max(len(current_lines) - len(target_lines), 0)

    validation_checks = [
        {
            "name": "target_version_available",
            "passed": bool(target_version),
            "severity": "error",
        },
        {
            "name": "current_file_available",
            "passed": bool(current_file),
            "severity": "error",
        },
        {
            "name": "path_matches_current_file",
            "passed": target_version.get("path") == current_file.get("path"),
            "severity": "error",
        },
        {
            "name": "language_matches_current_file",
            "passed": target_version.get("language") == current_file.get("language"),
            "severity": "warning",
        },
        {
            "name": "dry_run_only",
            "passed": True,
            "severity": "info",
        },
        {
            "name": "no_db_content_mutation",
            "passed": True,
            "severity": "info",
        },
        {
            "name": "no_disk_write",
            "passed": True,
            "severity": "info",
        },
        {
            "name": "no_generated_code_execution",
            "passed": True,
            "severity": "info",
        },
    ]

    blocking_issue_count = sum(
        1
        for check in validation_checks
        if check["severity"] == "error" and not check["passed"]
    )

    risk_level = "low"
    if not content_would_change:
        risk_level = "none"
    elif blocking_issue_count:
        risk_level = "high"
    elif added_line_count + removed_line_count > 25:
        risk_level = "medium"

    simulation = {
        "simulation_type": "generated_file_version_restore",
        "simulation_mode": "dry_run_only",
        "planned_action": "replace_db_preview_content",
        "would_restore": blocking_issue_count == 0,
        "would_change_content": content_would_change,
        "would_change_hash": hash_would_change,
        "risk_level": risk_level,
        "blocking_issue_count": blocking_issue_count,
        "validation_checks": validation_checks,
        "impact_report": {
            "generated_file_id": current_file.get("generated_file_id"),
            "target_version_id": target_version_id,
            "path": current_file.get("path") or target_version.get("path"),
            "language": current_file.get("language") or target_version.get("language"),
            "current_content_hash": current_hash,
            "target_content_hash": target_hash,
            "current_line_count": len(current_lines),
            "target_line_count": len(target_lines),
            "added_line_count": added_line_count,
            "removed_line_count": removed_line_count,
        },
        "before_preview": {
            "content_preview": current_content,
            "content_hash": current_hash,
        },
        "after_preview": {
            "content_preview": target_content,
            "content_hash": target_hash,
        },
    }

    return {
        "success": True,
        "found": True,
        "target_version_id": target_version_id,
        "simulation_mode": "dry_run_only",
        "write_mode": "db_preview_only",
        "restore_execution_supported": False,
        "restore_execution_performed": False,
        "db_content_mutation_performed": False,
        "disk_write_performed": False,
        "generated_code_execution_performed": False,
        "simulation": simulation,
        "restore_plan": plan,
    }
