from __future__ import annotations

import argparse
import json
from typing import Any, Dict

from app.platform.agents.app_build_request_run_check import run_app_build_request
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.services.customer_app_scope_service import draft_and_approve_customer_app_scope
from app.platform.services.generated_file_persistence_service import (
    get_persisted_generated_file,
    update_persisted_generated_file_content,
)
from app.platform.services.generated_file_version_service import (
    create_generated_file_version_snapshot,
    list_generated_file_versions,
)


def run_generated_file_review_edit_flow_check(
    *,
    app_request: str,
    real_bridge: bool = True,
) -> Dict[str, Any]:
    create_platform_tables()
    scope_db = PlatformSessionLocal()
    try:
        scope = draft_and_approve_customer_app_scope(
            scope_db,
            app_request=app_request,
            requested_by="v89_generated_file_review_edit_flow_check",
        )
    finally:
        scope_db.close()

    build_result = run_app_build_request(
        app_request=app_request,
        scoping_request_id=scope["scoping_request_id"],
        real_bridge=real_bridge,
    )

    summary = build_result.get("summary") or {}
    persistence = summary.get("generated_file_persistence") or {}
    generated_files = persistence.get("generated_files") or []

    selected_file = next(
        (file for file in generated_files if file.get("path") == "README.md"),
        generated_files[0] if generated_files else None,
    )

    if not selected_file:
        return {
            "success": False,
            "reason": "no_generated_file_available",
            "build_result": build_result,
        }

    generated_file_id = str(selected_file.get("generated_file_id"))
    db = PlatformSessionLocal()
    try:
        before_file = get_persisted_generated_file(db, generated_file_id)
        before_content = ((before_file.get("generated_file") or {}).get("content_preview")) or ""
        edited_content = (
            before_content
            + "\n\n## Browser Edit Smoke Check\n\n"
            + "V89 verified DB-preview editing and version snapshot creation.\n"
        )

        update_result = update_persisted_generated_file_content(
            db,
            generated_file_id,
            edited_content,
            editor_id="v89_generated_file_review_edit_flow_check",
        )

        snapshot_result = create_generated_file_version_snapshot(
            db,
            generated_file_id=generated_file_id,
            snapshot_status="browser_editor_saved",
            restore_status="not_restored",
            metadata={
                "snapshot_reason": "v89_browser_review_edit_flow_check",
                "created_by": "v89_smoke_check",
            },
        )

        after_file = get_persisted_generated_file(db, generated_file_id)
        versions_result = list_generated_file_versions(db, generated_file_id)
    finally:
        db.close()

    after_content = ((after_file.get("generated_file") or {}).get("content_preview")) or ""
    versions = versions_result.get("generated_file_versions") or []

    safety_ok = (
        update_result.get("write_mode") == "db_preview_only"
        and update_result.get("disk_write_performed") is False
        and update_result.get("generated_code_execution_performed") is False
    )

    passed = (
        build_result.get("success") is True
        and summary.get("generated_file_count", 0) >= 4
        and update_result.get("updated") is True
        and snapshot_result.get("snapshot_created") is True
        and len(versions) >= 1
        and "V89 verified DB-preview editing" in after_content
        and safety_ok
    )

    return {
        "success": passed,
        "milestone": "V89",
        "app_request": app_request,
        "workflow_run_id": summary.get("workflow_run_id"),
        "generated_file_count": summary.get("generated_file_count"),
        "selected_generated_file_id": generated_file_id,
        "selected_path": selected_file.get("path"),
        "edit_updated": update_result.get("updated"),
        "snapshot_created": snapshot_result.get("snapshot_created"),
        "version_count": versions_result.get("version_count", len(versions)),
        "safety": {
            "write_mode": update_result.get("write_mode"),
            "disk_write_performed": update_result.get("disk_write_performed"),
            "generated_code_execution_performed": update_result.get("generated_code_execution_performed"),
        },
        "checks": {
            "build_success": build_result.get("success") is True,
            "generated_file_count_ok": summary.get("generated_file_count", 0) >= 4,
            "edit_saved": update_result.get("updated") is True,
            "snapshot_created": snapshot_result.get("snapshot_created") is True,
            "version_history_available": len(versions) >= 1,
            "edited_content_loaded": "V89 verified DB-preview editing" in after_content,
            "safety_ok": safety_ok,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="V89 smoke check for DB-preview generated file review/edit/version flow."
    )
    parser.add_argument(
        "app_request",
        nargs="?",
        default="Build me a simple booking app for yoga classes",
    )
    parser.add_argument(
        "--simulation",
        action="store_true",
        help="Run app-build workflow in simulation mode instead of real bridge mode.",
    )
    args = parser.parse_args()

    result = run_generated_file_review_edit_flow_check(
        app_request=args.app_request,
        real_bridge=not args.simulation,
    )
    print(json.dumps(result, indent=2, sort_keys=True))

    if not result.get("success"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
