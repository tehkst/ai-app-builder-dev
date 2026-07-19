from __future__ import annotations

import json
import os
import shutil
import uuid
import hashlib
import base64
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

from sqlalchemy import and_, or_, update

from app.platform.persistence.database import PlatformSessionLocal
from app.platform.persistence.execution_migrations import run_execution_layer_migrations
from app.platform.persistence.models import PlatformExecutionWorkspace, PlatformWorkspaceArtifact


WORKSPACE_ROOT = Path(os.getenv("PLATFORM_EXECUTION_WORKSPACE_ROOT", "/tmp/ai-software-factory-workspaces"))


def create_workspace(payload: Dict[str, Any]) -> Dict[str, Any]:
    run_execution_layer_migrations()
    now = _now()
    workspace_id = str(payload.get("workspace_id") or "WORKSPACE-%s" % uuid.uuid4().hex[:12].upper())
    path = WORKSPACE_ROOT / workspace_id
    path.mkdir(parents=True, exist_ok=False)
    record = PlatformExecutionWorkspace(
        workspace_id=workspace_id, mission_id=str(payload.get("mission_id") or "").strip(),
        owner_id=str(payload.get("owner_id") or "mission_control"), repository=str(payload.get("repository") or "tehkst/ai-app-builder-dev"),
        branch=str(payload.get("branch") or "main"), local_path=str(path), status="created",
        retention_until=now + timedelta(hours=max(1, int(payload.get("retention_hours") or 24))),
        metadata_json=json.dumps(payload.get("metadata") or {}, sort_keys=True), recovery_json="{}", created_at=now, updated_at=now,
    )
    if not record.mission_id:
        shutil.rmtree(path, ignore_errors=True)
        return {"status": "invalid", "error": "mission_id is required."}
    with PlatformSessionLocal() as db:
        db.add(record); db.commit()
    return inspect_workspace(workspace_id)


def inspect_workspace(workspace_id: str) -> Dict[str, Any]:
    with PlatformSessionLocal() as db:
        record = db.query(PlatformExecutionWorkspace).filter_by(workspace_id=workspace_id).first()
        return _workspace(record) if record else {"status": "not-found", "workspace_id": workspace_id}


def acquire_workspace_lease(workspace_id: Any, owner_id: str = "", lease_seconds: int = 120) -> Dict[str, Any]:
    if isinstance(workspace_id, dict):
        payload = workspace_id; workspace_id = str(payload.get("workspace_id") or ""); owner_id = str(payload.get("owner_id") or payload.get("actor") or "mission_control"); lease_seconds = int(payload.get("lease_seconds") or lease_seconds)
    now = _now(); expires = now + timedelta(seconds=max(30, min(lease_seconds, 900)))
    with PlatformSessionLocal() as db:
        result = db.execute(update(PlatformExecutionWorkspace).where(and_(
            PlatformExecutionWorkspace.workspace_id == workspace_id,
            or_(PlatformExecutionWorkspace.lease_owner.is_(None), PlatformExecutionWorkspace.lease_expires_at <= now, PlatformExecutionWorkspace.lease_owner == owner_id),
        )).values(lease_owner=owner_id, lease_expires_at=expires, heartbeat_at=now, status="leased", updated_at=now))
        db.commit()
        return {"acquired": result.rowcount == 1, "workspace_id": workspace_id, "lease_owner": owner_id, "lease_expires_at": expires.isoformat() if result.rowcount else None}


def heartbeat_workspace(workspace_id: Any, owner_id: str = "", lease_seconds: int = 120) -> Dict[str, Any]:
    if isinstance(workspace_id, dict):
        payload = workspace_id; workspace_id = str(payload.get("workspace_id") or ""); owner_id = str(payload.get("owner_id") or payload.get("actor") or "mission_control"); lease_seconds = int(payload.get("lease_seconds") or lease_seconds)
    now = _now(); expires = now + timedelta(seconds=lease_seconds)
    with PlatformSessionLocal() as db:
        result = db.execute(update(PlatformExecutionWorkspace).where(and_(PlatformExecutionWorkspace.workspace_id == workspace_id, PlatformExecutionWorkspace.lease_owner == owner_id, PlatformExecutionWorkspace.lease_expires_at > now)).values(heartbeat_at=now, lease_expires_at=expires, updated_at=now))
        db.commit(); return {"renewed": result.rowcount == 1, "workspace_id": workspace_id}


def recover_workspace(workspace_id: Any) -> Dict[str, Any]:
    if isinstance(workspace_id, dict): workspace_id = str(workspace_id.get("workspace_id") or "")
    state = inspect_workspace(workspace_id)
    if state.get("status") == "not-found": return state
    path = Path(str(state.get("local_path") or ""))
    path.mkdir(parents=True, exist_ok=True)
    with PlatformSessionLocal() as db:
        db.execute(update(PlatformExecutionWorkspace).where(PlatformExecutionWorkspace.workspace_id == workspace_id).values(status="recovered", recovery_json=json.dumps({"recovered_at": _now().isoformat()}), updated_at=_now())); db.commit()
    return inspect_workspace(workspace_id)


def cleanup_expired_workspaces(payload: Any = None) -> Dict[str, Any]:
    now = _now(); cleaned = []
    with PlatformSessionLocal() as db:
        records = db.query(PlatformExecutionWorkspace).filter(PlatformExecutionWorkspace.retention_until < now, PlatformExecutionWorkspace.status != "destroyed").all()
        for record in records:
            shutil.rmtree(record.local_path or "", ignore_errors=True); record.status = "cleaned"; record.updated_at = now; cleaned.append(record.workspace_id)
        db.commit()
    return {"status": "completed", "cleaned": cleaned}


def destroy_workspace(workspace_id: Any, owner_id: str = "") -> Dict[str, Any]:
    if isinstance(workspace_id, dict):
        payload = workspace_id; workspace_id = str(payload.get("workspace_id") or ""); owner_id = str(payload.get("owner_id") or payload.get("actor") or "mission_control")
    state = inspect_workspace(workspace_id)
    if state.get("owner_id") != owner_id: return {"status": "denied", "reason": "Workspace ownership mismatch."}
    shutil.rmtree(str(state.get("local_path") or ""), ignore_errors=True)
    with PlatformSessionLocal() as db:
        db.execute(update(PlatformExecutionWorkspace).where(PlatformExecutionWorkspace.workspace_id == workspace_id).values(status="destroyed", lease_owner=None, lease_expires_at=None, updated_at=_now())); db.commit()
    return {"status": "destroyed", "workspace_id": workspace_id}


def record_workspace_artifact(workspace_id: str, artifact_type: str, path: str, content: bytes, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    run_execution_layer_migrations()
    record = PlatformWorkspaceArtifact(
        artifact_id="ARTIFACT-%s" % uuid.uuid4().hex[:16].upper(), workspace_id=workspace_id,
        artifact_type=artifact_type, path=path, sha256=hashlib.sha256(content).hexdigest(),
        content_base64=base64.b64encode(content).decode("ascii"),
        metadata_json=json.dumps(metadata or {}, sort_keys=True),
    )
    with PlatformSessionLocal() as db:
        db.add(record); db.commit()
        return {"artifact_id": record.artifact_id, "workspace_id": workspace_id, "sha256": record.sha256}


def _workspace(record: Any) -> Dict[str, Any]:
    return {"status": record.status, "workspace_id": record.workspace_id, "mission_id": record.mission_id, "owner_id": record.owner_id, "repository": record.repository, "branch": record.branch, "local_path": record.local_path, "lease_owner": record.lease_owner, "heartbeat_at": record.heartbeat_at.isoformat() if record.heartbeat_at else None, "recovery": json.loads(record.recovery_json or "{}")}


def _now() -> datetime: return datetime.now(timezone.utc)
