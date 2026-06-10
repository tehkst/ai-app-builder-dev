# Split from the legacy module to keep each Python file under 200 lines.
from __future__ import annotations
import json
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.platform.persistence.models import (
    PlatformWorkflowRun,
    PlatformWorkflowStepRun,
    utc_now,
)

def _json_dump(value: Any, fallback: Any) -> str:
    if value is None:
        value = fallback
    return json.dumps(value, sort_keys=True)

def _selected_agent_id(step_run: Dict[str, Any]) -> Optional[str]:
    selected_agent = step_run.get("selected_agent") or {}
    if isinstance(selected_agent, dict):
        return selected_agent.get("agent_id")
    return None
