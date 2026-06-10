# Split from the legacy module to keep each Python file under 200 lines.
from __future__ import annotations
import json
from typing import Any, Dict
from fastapi.testclient import TestClient
from app.main import app
from app.platform.api.security import require_platform_admin
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import PlatformGeneratedFile, utc_now
from app.platform.services.generated_file_persistence_service import (
    persist_generated_files_for_workflow,
)
from app.platform.services.generated_file_version_service import (
    create_generated_file_version_snapshot,
)
from app.platform.services.workflow_run_persistence_service import get_workflow_run_detail

def _create_approval(client: TestClient) -> Dict[str, Any]:
    run_response = client.post(
        "/platform/app-build/run",
        json={
            "app_request": "Build me a simple approval decision app",
            "real_bridge": True,
        },
    )
    run_data = run_response.json()
    workflow_run_id = (run_data.get("summary") or {}).get("workflow_run_id")

    persist_result: Dict[str, Any] = {}
    first_generated_file_id = None
    first_version_id = None

    if workflow_run_id:
        db = PlatformSessionLocal()
        try:
            detail = get_workflow_run_detail(db, workflow_run_id=workflow_run_id)
            persist_result = persist_generated_files_for_workflow(
                db,
                detail,
                workspace_id=f"workspace_{workflow_run_id}",
                project_id="project_restore_approval_decision_check",
            )

            generated_files = persist_result.get("generated_files") or []
            first_generated_file_id = (
                generated_files[0].get("generated_file_id")
                if generated_files
                else None
            )

            if first_generated_file_id:
                snapshot = create_generated_file_version_snapshot(
                    db,
                    first_generated_file_id,
                )
                first_version_id = snapshot.get("generated_file_version_id")

                file_record = (
                    db.query(PlatformGeneratedFile)
                    .filter(
                        PlatformGeneratedFile.generated_file_id
                        == first_generated_file_id
                    )
                    .first()
                )
                if file_record:
                    file_record.content_preview = (
                        (file_record.content_preview or "")
                        + "\\nCurrent DB preview changed before approval decision."
                    )
                    file_record.content_hash = (
                        "current_changed_for_approval_decision_"
                        + first_generated_file_id[-8:]
                    )
                    file_record.updated_at = utc_now()
                    db.commit()
        finally:
            db.close()

    approval_response = client.post(
        f"/platform/app-build/generated-file-versions/{first_version_id}/restore-approval-requests"
    ) if first_version_id else None
    approval_data = approval_response.json() if approval_response is not None else {}
    approval = approval_data.get("approval_request") or {}

    return {
        "workflow_run_id": workflow_run_id,
        "first_generated_file_id": first_generated_file_id,
        "first_version_id": first_version_id,
        "approval_id": approval.get("approval_id"),
        "persist_result": persist_result,
        "approval_data": approval_data,
    }
