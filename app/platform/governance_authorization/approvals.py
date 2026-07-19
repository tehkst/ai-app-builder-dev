from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from sqlalchemy import and_, update

from app.platform.persistence.database import PlatformSessionLocal
from app.platform.persistence.execution_migrations import run_execution_layer_migrations
from app.platform.persistence.models import PlatformGovernanceApproval
from app.platform.auth.service import require_founder


def create_durable_approval(payload: Dict[str, Any]) -> Dict[str, Any]:
    run_execution_layer_migrations()
    founder = require_founder(payload)
    if not founder.get("authorized"):
        return {"status": "denied", "error": "Valid founder authorization is required."}
    now = _now()
    ttl = max(1, min(int(payload.get("ttl_minutes") or 30), 1440))
    record = PlatformGovernanceApproval(
        approval_id=str(payload.get("approval_id") or "APPROVAL-%s" % uuid.uuid4().hex[:12].upper()),
        mission_id=str(payload.get("mission_id") or "").strip(),
        action=str(payload.get("action") or "").strip(),
        scope=str(payload.get("scope") or "mission").strip(),
        target=str(payload.get("target") or "").strip(),
        approved_by=str(founder.get("founder_id") or founder.get("role") or "founder").strip(),
        approved_at=now,
        expires_at=now + timedelta(minutes=ttl),
        metadata_json=json.dumps(payload.get("metadata") or {}, sort_keys=True),
        created_at=now,
        updated_at=now,
    )
    if not record.mission_id or not record.action or not record.target:
        return {"status": "invalid", "error": "mission_id, action, and target are required."}
    with PlatformSessionLocal() as db:
        db.add(record)
        db.commit()
        return _approval(record)


def consume_durable_approval(approval_id: str, mission_id: str, action: str, target: str) -> Dict[str, Any]:
    run_execution_layer_migrations()
    now = _now()
    with PlatformSessionLocal() as db:
        result = db.execute(
            update(PlatformGovernanceApproval)
            .where(and_(
                PlatformGovernanceApproval.approval_id == approval_id,
                PlatformGovernanceApproval.mission_id == mission_id,
                PlatformGovernanceApproval.action == action,
                PlatformGovernanceApproval.target == target,
                PlatformGovernanceApproval.consumed_at.is_(None),
                PlatformGovernanceApproval.revoked_at.is_(None),
                PlatformGovernanceApproval.expires_at > now,
            ))
            .values(consumed_at=now, updated_at=now)
        )
        if result.rowcount != 1:
            db.rollback()
            return {"consumed": False, "reason": "Approval is missing, expired, revoked, consumed, or outside its approved scope."}
        db.commit()
        return {"consumed": True, "approval_id": approval_id, "consumed_at": now.isoformat()}


def revoke_durable_approval(approval_id: Any) -> Dict[str, Any]:
    if isinstance(approval_id, dict):
        payload = approval_id
        if not require_founder(payload).get("authorized"):
            return {"revoked": False, "reason": "Valid founder authorization is required."}
        approval_id = str(payload.get("approval_id") or "")
    now = _now()
    with PlatformSessionLocal() as db:
        result = db.execute(
            update(PlatformGovernanceApproval)
            .where(and_(PlatformGovernanceApproval.approval_id == approval_id, PlatformGovernanceApproval.consumed_at.is_(None)))
            .values(revoked_at=now, updated_at=now)
        )
        db.commit()
        return {"revoked": result.rowcount == 1, "approval_id": approval_id}


def _approval(record: PlatformGovernanceApproval) -> Dict[str, Any]:
    return {
        "status": "approved", "approval_id": record.approval_id, "mission_id": record.mission_id,
        "action": record.action, "scope": record.scope, "target": record.target,
        "approved_by": record.approved_by, "approved_at": record.approved_at.isoformat(),
        "expires_at": record.expires_at.isoformat() if record.expires_at else None,
        "consumed_at": record.consumed_at.isoformat() if record.consumed_at else None,
        "revoked_at": record.revoked_at.isoformat() if record.revoked_at else None,
    }


def _now() -> datetime:
    return datetime.now(timezone.utc)
