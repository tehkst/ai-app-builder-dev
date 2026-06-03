import json
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.platform.persistence.models import PlatformAuditEvent


def encode_metadata(metadata: Optional[Dict[str, Any]]) -> str:
    return json.dumps(metadata or {})


def create_audit_event(
    db: Session,
    *,
    event_type: str,
    status: str,
    actor_type: str = "system",
    actor_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    project_id: Optional[str] = None,
    route: Optional[str] = None,
    auth_mode: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> PlatformAuditEvent:
    event = PlatformAuditEvent(
        event_type=event_type,
        actor_type=actor_type,
        actor_id=actor_id,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        project_id=project_id,
        status=status,
        route=route,
        auth_mode=auth_mode,
        metadata_json=encode_metadata(metadata),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_audit_events(db: Session, limit: int = 100) -> List[PlatformAuditEvent]:
    safe_limit = max(1, min(limit, 100))

    return (
        db.query(PlatformAuditEvent)
        .order_by(PlatformAuditEvent.id.desc())
        .limit(safe_limit)
        .all()
    )
