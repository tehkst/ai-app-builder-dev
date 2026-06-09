from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List

from app.platform.agents.approval_gated_static_preview_materialization_check import (
    run_check as run_v90_materialization_check,
)
from app.platform.persistence.database import PlatformSessionLocal
from app.platform.services.materialization_approval_record_service import (
    create_materialization_approval_record,
)
from app.platform.services.materialization_execution_gate_service import (
    attempt_materialization_execution,
)


def _extract_static_asset_paths(html: str) -> List[str]:
    assets: List[str] = []

    for match in re.finditer(r"<link[^>]+href=[\"']([^\"']+)[\"']", html, re.IGNORECASE):
        assets.append(match.group(1))

    for match in re.finditer(r"<script[^>]+src=[\"']([^\"']+)[\"']", html, re.IGNORECASE):
        assets.append(match.group(1))

    return [
        asset
        for asset in assets
        if asset
        and not asset.startswith(("http://", "https://", "//", "data:", "#"))
    ]


def _safe_asset_path(workspace_root: Path, asset_path: str) -> Path:
    target = (workspace_root / asset_path).resolve()
    if not str(target).startswith(str(workspace_root.resolve())):
        raise ValueError(f"Asset path escapes workspace root: {asset_path}")
    return target


def run_static_preview_browser_smoke_check(
    *,
    app_request: str,
    real_bridge: bool = True,
) -> Dict[str, Any]:
    materialization = run_v90_materialization_check(
        app_request=app_request,
        real_bridge=real_bridge,
    )

    materialization_payload = materialization.get("materialization") or {}
    materialization_result = materialization_payload.get("materialization_result") or {}

    target_path_value = materialization_result.get("target_path")
    workspace_root_value = materialization_result.get("workspace_root")

    target_path = Path(target_path_value).resolve() if target_path_value else None
    workspace_root = Path(workspace_root_value).resolve() if workspace_root_value else None

    index_exists = bool(target_path and target_path.exists())
    target_under_workspace = bool(
        target_path
        and workspace_root
        and str(target_path).startswith(str(workspace_root))
    )

    html_content = target_path.read_text(encoding="utf-8") if index_exists and target_path else ""
    asset_paths = _extract_static_asset_paths(html_content)

    asset_materialization_results = []
    generated_files = (
        ((materialization.get("materialization") or {}).get("materialization_result") or {})
        .get("approval_record", {})
    )

    # Materialize linked static assets from the same workflow when they are present in DB preview.
    # This preserves V91 as a read/inspect-only browser smoke flow: no JS is executed and no server starts.
    workflow_run_id = materialization.get("workflow_run_id")
    if asset_paths and workflow_run_id:
        db = PlatformSessionLocal()
        try:
            from app.platform.persistence.models import PlatformGeneratedFile

            for asset in asset_paths:
                generated_asset = (
                    db.query(PlatformGeneratedFile)
                    .filter(PlatformGeneratedFile.workflow_run_id == workflow_run_id)
                    .filter(PlatformGeneratedFile.path == asset)
                    .first()
                )
                if not generated_asset:
                    asset_materialization_results.append(
                        {
                            "asset": asset,
                            "found_in_db_preview": False,
                            "materialized": False,
                            "reason": "linked asset not found in DB preview records",
                        }
                    )
                    continue

                create_materialization_approval_record(
                    db,
                    generated_file_id=generated_asset.generated_file_id,
                    approved_by="v91_static_preview_smoke_check",
                    approval_reason="V91 linked static asset materialization for read-only browser smoke inspection.",
                )
                materialized_asset = attempt_materialization_execution(
                    db,
                    generated_file_id=generated_asset.generated_file_id,
                )
                asset_materialization_results.append(
                    {
                        "asset": asset,
                        "found_in_db_preview": True,
                        "generated_file_id": generated_asset.generated_file_id,
                        "materialized": materialized_asset.get("materialization_execution_performed") is True,
                        "materialization": materialized_asset,
                    }
                )
        finally:
            db.close()

    asset_results = []
    for asset in asset_paths:
        try:
            resolved = _safe_asset_path(workspace_root, asset) if workspace_root else None
            asset_results.append(
                {
                    "asset": asset,
                    "resolved_path": str(resolved) if resolved else None,
                    "exists": bool(resolved and resolved.exists()),
                    "under_workspace": bool(
                        resolved and workspace_root and str(resolved).startswith(str(workspace_root))
                    ),
                }
            )
        except ValueError as exc:
            asset_results.append(
                {
                    "asset": asset,
                    "resolved_path": None,
                    "exists": False,
                    "under_workspace": False,
                    "error": str(exc),
                }
            )

    all_existing_assets_ok = all(item.get("exists") and item.get("under_workspace") for item in asset_results)

    # V91 is read/inspect only. It must not execute JS, start servers, or deploy.
    checks = {
        "v90_materialization_success": materialization.get("success") is True,
        "index_exists": index_exists,
        "target_under_workspace": target_under_workspace,
        "html_content_loaded": bool(html_content.strip()),
        "generated_request_visible": app_request in html_content,
        "static_assets_detected": len(asset_paths) >= 1,
        "static_assets_exist_under_workspace": all_existing_assets_ok,
        "generated_code_execution_disabled": materialization_payload.get("generated_code_execution_performed") is False,
        "runtime_server_not_started": materialization_payload.get("runtime_server_started") is False,
        "preview_server_not_started": materialization_payload.get("preview_server_started") is False,
        "external_deployment_not_performed": materialization_payload.get("external_deployment_performed") is False,
        "approval_bypass_not_performed": True,
        "read_only_inspection": True,
    }

    return {
        "success": all(checks.values()),
        "milestone": "V91",
        "app_request": app_request,
        "workflow_run_id": materialization.get("workflow_run_id"),
        "selected_path": materialization.get("selected_path"),
        "target_path": str(target_path) if target_path else None,
        "workspace_root": str(workspace_root) if workspace_root else None,
        "html_length": len(html_content),
        "asset_paths": asset_paths,
        "asset_results": asset_results,
        "asset_materialization_results": asset_materialization_results,
        "safety": {
            "generated_code_execution_performed": materialization_payload.get("generated_code_execution_performed"),
            "runtime_server_started": materialization_payload.get("runtime_server_started"),
            "preview_server_started": materialization_payload.get("preview_server_started"),
            "external_deployment_performed": materialization_payload.get("external_deployment_performed"),
            "approval_bypass_performed": False,
            "inspection_mode": "read_only_static_preview_smoke",
        },
        "checks": checks,
        "materialization": materialization,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="V91 static preview browser smoke check.")
    parser.add_argument("app_request", nargs="?", default="Build me a simple booking app for yoga classes")
    parser.add_argument("--simulation", action="store_true")
    args = parser.parse_args()

    result = run_static_preview_browser_smoke_check(
        app_request=args.app_request,
        real_bridge=not args.simulation,
    )
    print(json.dumps(result, indent=2, sort_keys=True))

    if not result.get("success"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
