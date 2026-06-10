from __future__ import annotations

import json
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.platform.persistence.models import PlatformAuditEvent


def log_workflow_event(
    db: Session,
    *,
    status: str,
    metadata: Dict[str, Any],
) -> None:
    event = PlatformAuditEvent(
        event_type="agent_workflow_execution",
        actor_type="system",
        actor_id="agent_workflow_executor_service",
        status=status,
        metadata_json=json.dumps(metadata, sort_keys=True),
    )
    db.add(event)
    db.commit()
