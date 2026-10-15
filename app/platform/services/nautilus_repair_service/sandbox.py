"""Resolve the sandbox a Nautilus repair may work on, from the workflow run itself.

Callers never supply a directory: the workspace comes from the workflow's generated files
(the same resolver the controlled runtime uses) and must sit inside the approved sandbox base,
so an arbitrary server directory can't be copied into an agent run and sent to the model.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.platform.services.controlled_runtime_workspace import workspace_root_for_workflow
from app.platform.services.materialization_sandbox_writer_service import APPROVED_SANDBOX_ROOT_BASE


def within_approved_base(path: Path, base: Optional[Path] = None) -> bool:
    root = (base or APPROVED_SANDBOX_ROOT_BASE).resolve()
    resolved = path.resolve()
    return resolved != root and root in resolved.parents


def resolve_workflow_sandbox(db: Session, workflow_run_id: str) -> Tuple[Optional[Path], Optional[str]]:
    """(sandbox path, None) when valid, otherwise (None, reason)."""
    workspace = workspace_root_for_workflow(db, workflow_run_id)
    if not workspace:
        return None, "Workspace root could not be resolved from this workflow's generated files."
    workspace = Path(workspace).resolve()
    if not within_approved_base(workspace):
        return None, "Workspace root is outside the approved sandbox base."
    if not workspace.is_dir():
        return None, "Workspace root does not exist. Materialize approved files first."
    return workspace, None
