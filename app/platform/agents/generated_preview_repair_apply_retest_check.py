from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any, Dict

from app.platform.services.generated_preview_repair_apply_service import (
    apply_generated_preview_repair,
    approve_generated_preview_repair,
    retest_generated_preview_repair,
)


def run_generated_preview_repair_apply_retest_check() -> Dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="v93-generated-preview-repair-") as workspace:
        workspace_root = str(Path(workspace).resolve())
        diagnostics = {
            "html_content_loaded": True,
            "generated_request_visible": True,
            "target_under_workspace": True,
            "asset_results": [
                {
                    "asset": "missing-assets.css",
                    "exists": False,
                    "under_workspace": True,
                    "resolved_path": str(Path(workspace_root) / "missing-assets.css"),
                }
            ],
        }

        blocked = apply_generated_preview_repair(
            workflow_run_id="v93-generated-preview-repair-apply-retest",
            selected_path="index.html",
            diagnostics=diagnostics,
            workspace_root=workspace_root,
            approval=None,
        )

        approval = approve_generated_preview_repair(
            approved_by="v93_smoke_check",
            approval_reason="Approve generated preview repair apply for V93 smoke check.",
        )

        applied = apply_generated_preview_repair(
            workflow_run_id="v93-generated-preview-repair-apply-retest",
            selected_path="index.html",
            diagnostics=diagnostics,
            workspace_root=workspace_root,
            approval=approval,
        )

        retest = retest_generated_preview_repair(
            target_path=str(applied.get("target_path")),
            workspace_root=workspace_root,
        )

    checks = {
        "blocked_before_approval": blocked.get("repair_apply_status") == "blocked"
        and blocked.get("repair_actions_applied") is False,
        "approval_recorded": approval.get("approved") is True
        and approval.get("approval_bypass_performed") is False,
        "repair_applied_after_approval": applied.get("repair_apply_status") == "applied"
        and applied.get("repair_actions_applied") is True,
        "target_exists_after_apply": applied.get("target_exists_after_apply") is True,
        "target_under_workspace_after_apply": applied.get("target_under_workspace_after_apply") is True,
        "retest_passed": retest.get("success") is True and retest.get("retest_status") == "passed",
        "generated_code_not_executed": applied.get("generated_code_execution_performed") is False
        and retest.get("generated_code_execution_performed") is False,
        "runtime_not_started": applied.get("runtime_server_started") is False
        and retest.get("runtime_server_started") is False,
        "preview_not_started": applied.get("preview_server_started") is False
        and retest.get("preview_server_started") is False,
        "external_deployment_not_performed": applied.get("external_deployment_performed") is False
        and retest.get("external_deployment_performed") is False,
        "approval_not_bypassed": applied.get("approval_bypass_performed") is False
        and retest.get("approval_bypass_performed") is False,
    }

    return {
        "success": all(checks.values()),
        "milestone": "V93",
        "checks": checks,
        "blocked_before_approval": blocked,
        "approval": approval,
        "applied": applied,
        "retest": retest,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="V93 generated preview repair apply and re-test smoke check.")
    parser.parse_args()

    result = run_generated_preview_repair_apply_retest_check()
    print(json.dumps(result, indent=2, sort_keys=True))

    if not result.get("success"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
