# Split from the legacy module to keep each Python file under 200 lines.
from __future__ import annotations
import json
import uuid
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from app.platform.agents.registry import get_agent
from app.platform.persistence.models import PlatformAuditEvent
SAFE_EXECUTION_AGENT_ALLOWLIST = {
    "test_agent",
    "orchestrator_agent",
    "architect_agent",
    "builder_agent",
    "reviewer_agent",
    "agent_factory_agent",
}

def _log_bridge_event(
    db: Session,
    *,
    status: str,
    metadata: Dict[str, Any],
) -> None:
    event = PlatformAuditEvent(
        event_type="agent_execution_bridge",
        actor_type="system",
        actor_id="agent_execution_bridge_service",
        status=status,
        metadata_json=json.dumps(metadata, sort_keys=True),
    )
    db.add(event)
    db.commit()

def _safe_task_payload(
    *,
    workflow_run_id: str,
    step_run: Dict[str, Any],
    workflow_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "task_id": f"bridge_task_{uuid.uuid4().hex}",
        "task_type": step_run.get("required_capability"),
        "title": step_run.get("title"),
        "description": step_run.get("title"),
        "input_payload": {
            "workflow_run_id": workflow_run_id,
            "step_id": step_run.get("step_id"),
            "step_run_id": step_run.get("step_run_id"),
            "required_capability": step_run.get("required_capability"),
            "workflow_context": workflow_context or {},
        },
    }
