from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List

from app.platform.auth.service import require_founder
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import PlatformGeneratedFile
from app.platform.services.scoping_persistence_service import (
    get_scoping_record,
    mark_publish_pull_request_created,
    serialize_scoping_record,
)

CONTRACT = "publish-materialization-v1"


def materialize_publish_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Turn an approved build's DB-preview generated files into a real GitHub PR
    targeting generated_apps/<app_id>/ - the same pattern ui_ux_agent's own
    approve_ui_change uses (github_execution.approved_executor), not a direct
    filesystem write: this container's own filesystem is ephemeral and wouldn't
    persist anyway, and a PR keeps the founder's real GitHub review as the actual
    checkpoint before anything from this build becomes a real, on-disk file. This
    only opens the PR; merging it is a separate, later founder action.
    """
    founder = require_founder(payload)
    if not founder.get("authorized"):
        return {"contract": CONTRACT, "status": "unauthorized", "authenticated": False}

    scoping_request_id = str(payload.get("scoping_request_id") or "").strip()
    if not scoping_request_id:
        return {"contract": CONTRACT, "status": "invalid-request", "error": "scoping_request_id is required."}

    create_platform_tables()
    with PlatformSessionLocal() as db:
        record = get_scoping_record(db, scoping_request_id)
        if record is None:
            return {"contract": CONTRACT, "status": "not_found", "scoping_request_id": scoping_request_id}
        if record.publish_status != "approved":
            return {
                "contract": CONTRACT, "status": "invalid_state", "scoping_request_id": scoping_request_id,
                "error": "This request must be approved (and not already materialized) first - current status: %s."
                % record.publish_status,
            }
        serialized = serialize_scoping_record(record)
        workflow_run_id = record.workflow_run_id
        app_id = record.publish_app_id or _new_app_id(_project_name(serialized))
        rows = _dedupe_latest(
            db.query(PlatformGeneratedFile).filter(PlatformGeneratedFile.workflow_run_id == workflow_run_id).all()
        )

    if not rows:
        return {
            "contract": CONTRACT, "status": "no_generated_files", "scoping_request_id": scoping_request_id,
            "error": "No generated files were found for this build's workflow run.",
        }

    file_changes: List[Dict[str, Any]] = []
    skipped: List[str] = []
    for row in rows:
        safe_suffix = _safe_original_path(row.path)
        if safe_suffix is None:
            skipped.append(row.path)
            continue
        file_changes.append({
            "path": "generated_apps/%s/%s" % (app_id, safe_suffix),
            "operation": "write",
            "content": row.content_preview or "",
        })
    if not file_changes:
        return {
            "contract": CONTRACT, "status": "no_safe_files", "scoping_request_id": scoping_request_id,
            "error": "Every generated file path was rejected as unsafe.", "skipped_paths": skipped,
        }

    project_name = _project_name(serialized)
    from app.platform.github_execution.approved_executor import execute_approved_github_execution

    execution_payload = dict(payload)
    execution_payload.update({
        "mission_id": "PUBLISH-%s" % scoping_request_id,
        "title": "Publish: %s" % project_name,
        "branch_name": "publish/%s" % app_id,
        "commit_message": "Materialize founder-approved build for %s into generated_apps/%s" % (project_name, app_id),
        "pr_title": "Publish: %s (generated_apps/%s)" % (project_name, app_id),
        "pr_body": (
            "Founder-approved customer build, ready for review before it can go live.\n\n"
            "Scoping request: %s\nWorkflow run: %s\n%s"
            % (
                scoping_request_id, workflow_run_id,
                ("Skipped %d unsafe file path(s): %s" % (len(skipped), ", ".join(skipped))) if skipped else "",
            )
        ),
        "file_changes": file_changes,
        "live_execution": True,
    })
    result = execute_approved_github_execution(execution_payload)

    if result.get("status") == "pull-request-created":
        with PlatformSessionLocal() as db:
            updated = mark_publish_pull_request_created(
                db,
                scoping_request_id=scoping_request_id,
                app_id=app_id,
                pull_request_url=str(result.get("pull_request_url") or ""),
                pull_request_number=int(result.get("pull_request_number") or 0),
            )
        return {
            "contract": CONTRACT, "status": "pull-request-created", "scoping_request_id": scoping_request_id,
            "app_id": app_id, "pull_request_url": result.get("pull_request_url"),
            "pull_request_number": result.get("pull_request_number"), "skipped_paths": skipped,
            "request": updated,
        }
    return {
        "contract": CONTRACT, "status": result.get("status") or "materialization-failed",
        "scoping_request_id": scoping_request_id, "app_id": app_id,
        "error": result.get("error") or result.get("recommended_action"),
    }


def _project_name(record: Dict[str, Any]) -> str:
    app_idea = str((record.get("normalized_request") or {}).get("app_idea") or "").strip()
    return app_idea[:60] if app_idea else "Untitled project"


def _new_app_id(project_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", project_name.lower()).strip("-")[:40] or "app"
    return "app-%s-%s" % (slug, uuid.uuid4().hex[:8])


def _dedupe_latest(rows: List[PlatformGeneratedFile]) -> List[PlatformGeneratedFile]:
    latest: Dict[str, PlatformGeneratedFile] = {}
    for row in rows:
        existing = latest.get(row.path)
        if existing is None or (row.updated_at and existing.updated_at and row.updated_at >= existing.updated_at):
            latest[row.path] = row
    return list(latest.values())


def _safe_original_path(path: str) -> str | None:
    """Reject an LLM-generated path that tries to escape generated_apps/<app_id>/.

    These paths are model output, not trusted input - defend here rather than rely
    solely on approved_executor's own path guard, so one bad path degrades to
    "skip this file" instead of failing the whole PR.
    """
    candidate = str(path or "").strip().lstrip("/")
    if not candidate or "\\" in candidate or ".." in candidate.split("/"):
        return None
    if candidate.split("/", 1)[0] == ".git":
        return None
    return candidate
