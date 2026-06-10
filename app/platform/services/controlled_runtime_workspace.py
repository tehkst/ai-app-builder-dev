from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.platform.persistence.models import PlatformGeneratedFile
from app.platform.services.materialization_sandbox_writer_service import APPROVED_SANDBOX_ROOT_BASE


def sanitize_workspace_id(workspace_id: str) -> str:
    safe = "".join(
        char if char.isalnum() or char in {"-", "_"} else "-"
        for char in workspace_id or "unknown-workspace"
    ).strip("-")
    return safe or "unknown-workspace"


def workspace_root_for_workflow(db: Session, workflow_run_id: str) -> Optional[Path]:
    generated_file = (
        db.query(PlatformGeneratedFile)
        .filter(PlatformGeneratedFile.workflow_run_id == workflow_run_id)
        .order_by(PlatformGeneratedFile.created_at.asc())
        .first()
    )
    if not generated_file or not generated_file.workspace_id:
        return None
    return APPROVED_SANDBOX_ROOT_BASE / sanitize_workspace_id(generated_file.workspace_id)


def resolve_working_directory(workspace_root: Path, run_plan: Dict[str, Any]) -> Optional[Path]:
    working_directory = (run_plan.get("working_directory") or ".").strip() or "."
    candidate = (workspace_root / working_directory).resolve()
    try:
        candidate.relative_to(workspace_root.resolve())
    except ValueError:
        return None
    return candidate
