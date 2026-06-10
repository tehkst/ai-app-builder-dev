# Split from the legacy module to keep each Python file under 200 lines.
from __future__ import annotations
import json
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.platform.persistence.database import PlatformSessionLocal, create_platform_tables
from app.platform.persistence.models import (
    PlatformModuleRolloutDecision,
    PlatformModuleRolloutEvent,
    PlatformSelfBuildModuleRequest,
    PlatformSelfBuildModuleRequestEvent,
    utc_now,
)
V82_PERSISTENT_STATE_SAFETY_MODE = "persistent_state_store_v82_db_backed_gate_preserving"

def list_module_rollout_events(request_id: str) -> List[Dict[str, Any]]:
    session = _session_scope()
    try:
        models = (
            session.query(PlatformModuleRolloutEvent)
            .filter(PlatformModuleRolloutEvent.request_id == request_id)
            .order_by(PlatformModuleRolloutEvent.id.asc())
            .all()
        )
        return [_rollout_event_to_dict(model) for model in models]
    finally:
        session.close()

def reset_v82_persistent_state_for_check() -> None:
    session = _session_scope()
    try:
        session.query(PlatformModuleRolloutEvent).delete()
        session.query(PlatformModuleRolloutDecision).delete()
        session.query(PlatformSelfBuildModuleRequestEvent).delete()
        session.query(PlatformSelfBuildModuleRequest).delete()
        session.commit()
    finally:
        session.close()
