from __future__ import annotations

import argparse
import json
from typing import Any, Dict

from app.platform.services.generated_preview_repair_proposal_service import (
    generate_generated_preview_repair_proposal,
)


def run_generated_preview_repair_proposal_check() -> Dict[str, Any]:
    diagnostics = {
        "html_content_loaded": True,
        "generated_request_visible": True,
        "target_under_workspace": True,
        "asset_results": [
            {
                "asset": "missing-assets.css",
                "exists": False,
                "under_workspace": True,
                "resolved_path": "/tmp/ai-software-factory/workspaces/example/missing-assets.css",
            }
        ],
    }

    result = generate_generated_preview_repair_proposal(
        workflow_run_id="v92-generated-preview-repair-proposal",
        selected_path="index.html",
        diagnostics=diagnostics,
    )

    proposal = result.get("repair_proposal") or {}
    proposal_items = proposal.get("proposal_items") or []

    checks = {
        "proposal_created": result.get("repair_proposal_created") is True,
        "proposal_only": proposal.get("proposal_only") is True,
        "issue_detected": result.get("issue_count") == 1,
        "missing_asset_proposed": any(
            item.get("issue_kind") == "missing_linked_static_asset"
            and item.get("target_file") == "missing-assets.css"
            for item in proposal_items
        ),
        "repair_actions_not_applied": result.get("repair_actions_applied") is False,
        "db_content_not_mutated": result.get("db_content_mutation_performed") is False,
        "filesystem_not_written": result.get("filesystem_write_performed") is False,
        "generated_code_not_executed": result.get("generated_code_execution_performed") is False,
        "runtime_not_started": result.get("runtime_server_started") is False,
        "preview_not_started": result.get("preview_server_started") is False,
        "external_deployment_not_performed": result.get("external_deployment_performed") is False,
        "approval_not_bypassed": result.get("approval_bypass_performed") is False,
    }

    return {
        "success": all(checks.values()),
        "milestone": "V92",
        "checks": checks,
        "proposal": result,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="V92 generated preview repair proposal smoke check.")
    parser.parse_args()

    result = run_generated_preview_repair_proposal_check()
    print(json.dumps(result, indent=2, sort_keys=True))

    if not result.get("success"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
