from __future__ import annotations

from typing import Any, Dict, List, Optional


GENERATED_PREVIEW_REPAIR_PROPOSAL_SAFETY_MODE = "generated_preview_repair_proposal_v92_proposal_only"


def _safe_flags() -> Dict[str, bool]:
    return {
        "repair_proposal_created": True,
        "repair_actions_applied": False,
        "db_content_mutation_performed": False,
        "filesystem_write_performed": False,
        "disk_write_performed": False,
        "generated_files_written_to_disk": False,
        "generated_code_execution_performed": False,
        "runtime_server_started": False,
        "preview_server_started": False,
        "external_deployment_performed": False,
        "approval_bypass_performed": False,
    }


def _issue_kind(issue: Dict[str, Any]) -> str:
    if issue.get("asset") and issue.get("exists") is False:
        return "missing_linked_static_asset"
    if issue.get("html_content_loaded") is False:
        return "empty_or_unreadable_preview_content"
    if issue.get("generated_request_visible") is False:
        return "generated_request_not_visible"
    if issue.get("target_under_workspace") is False:
        return "unsafe_or_unexpected_preview_path"
    return str(issue.get("kind") or "generated_preview_issue")


def _proposal_for_issue(issue: Dict[str, Any]) -> Dict[str, Any]:
    kind = _issue_kind(issue)
    asset = issue.get("asset")

    if kind == "missing_linked_static_asset":
        return {
            "issue_kind": kind,
            "target_file": str(asset),
            "proposed_change_summary": (
                f"Regenerate or materialize the missing linked static asset `{asset}`, "
                "or update the preview HTML reference to an existing approved static asset."
            ),
            "recommended_actions": [
                f"Verify `{asset}` exists as a DB-preview generated file.",
                f"If present, request approval-gated materialization for `{asset}` in a later apply milestone.",
                "If missing, propose regenerating the static asset content before any repair is applied.",
            ],
        }

    if kind == "empty_or_unreadable_preview_content":
        return {
            "issue_kind": kind,
            "target_file": str(issue.get("selected_path") or "index.html"),
            "proposed_change_summary": "Regenerate preview HTML content because the materialized preview is empty or unreadable.",
            "recommended_actions": [
                "Inspect DB-preview content for the selected generated file.",
                "Propose regenerating the static preview entrypoint content.",
            ],
        }

    if kind == "generated_request_not_visible":
        return {
            "issue_kind": kind,
            "target_file": str(issue.get("selected_path") or "index.html"),
            "proposed_change_summary": "Update the preview entrypoint so the generated app request is visible in the static preview.",
            "recommended_actions": [
                "Add the generated app request to the preview title, heading, or README-linked content.",
                "Keep the change static-only and approval-gated before apply.",
            ],
        }

    if kind == "unsafe_or_unexpected_preview_path":
        return {
            "issue_kind": kind,
            "target_file": str(issue.get("selected_path") or "unknown"),
            "proposed_change_summary": "Reject repair apply until the preview path is confirmed inside the guarded workspace sandbox.",
            "recommended_actions": [
                "Re-run path guard validation.",
                "Do not apply any file mutation until the target path is sandbox-bound.",
            ],
        }

    return {
        "issue_kind": kind,
        "target_file": str(issue.get("target_file") or issue.get("selected_path") or "generated preview file"),
        "proposed_change_summary": "Review generated preview diagnostics and prepare a targeted proposal before applying any change.",
        "recommended_actions": [
            "Inspect the diagnostic evidence.",
            "Prepare exact DB-preview file changes for later approval.",
        ],
    }


def generate_generated_preview_repair_proposal(
    *,
    workflow_run_id: Optional[str],
    selected_path: Optional[str],
    diagnostics: Dict[str, Any],
) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []

    if diagnostics.get("html_content_loaded") is False:
        issues.append({"html_content_loaded": False, "selected_path": selected_path})

    if diagnostics.get("generated_request_visible") is False:
        issues.append({"generated_request_visible": False, "selected_path": selected_path})

    if diagnostics.get("target_under_workspace") is False:
        issues.append({"target_under_workspace": False, "selected_path": selected_path})

    for asset_result in diagnostics.get("asset_results") or []:
        if asset_result.get("exists") is False or asset_result.get("under_workspace") is False:
            issues.append(dict(asset_result))

    proposal_items = [_proposal_for_issue(issue) for issue in issues]

    return {
        "success": True,
        "milestone": "V92",
        "workflow_run_id": workflow_run_id,
        "selected_path": selected_path,
        "safety_mode": GENERATED_PREVIEW_REPAIR_PROPOSAL_SAFETY_MODE,
        "diagnostic_source": "static_preview_browser_smoke_check",
        "issue_count": len(issues),
        "repair_proposal_created": True,
        "proposal_status": "proposal_created" if issues else "no_repair_needed",
        "repair_proposal": {
            "proposal_only": True,
            "repair_apply_milestone": "V93",
            "issues": issues,
            "proposal_items": proposal_items,
            "approval_requirements": [
                "User must review the proposal.",
                "No repair may be applied until V93 or a later explicitly approved apply milestone.",
                "Any future apply action must remain approval-gated and sandbox-bound.",
            ] if issues else [],
            "safety_notes": [
                "Proposal only.",
                "No generated files were mutated.",
                "No DB-preview content was changed.",
                "No filesystem writes were performed.",
                "No generated code was executed.",
            ],
        },
        **_safe_flags(),
    }
