# Split from the legacy module to keep each Python file under 200 lines.
from __future__ import annotations
import json
import re
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.platform.persistence.models import PlatformApprovalRequest, PlatformAuditEvent, utc_now
from app.platform.services.agent_dependency_graph_service import build_agent_dependency_graph
from app.platform.services.telegram_approval_service import (
    TelegramApprovalSendError,
    send_approval_to_telegram,
)
_CAPABILITY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*_task$")

def _title_from_capability(capability: str) -> str:
    base = capability.removesuffix("_task")
    words = [part for part in base.split("_") if part]
    return " ".join(word.capitalize() for word in words)

def _agent_id_from_capability(capability: str) -> str:
    base = capability.removesuffix("_task")
    return f"{base}_agent"

def _agent_name_from_capability(capability: str) -> str:
    return f"{_title_from_capability(capability)} Agent"

def _create_agent_factory_payload(capability: str) -> Dict[str, Any]:
    agent_id = _agent_id_from_capability(capability)
    agent_name = _agent_name_from_capability(capability)

    return {
        "proposed_agent": {
            "agent_id": agent_id,
            "name": agent_name,
            "description": (
                f"Plans and coordinates work for the missing capability: {capability}. "
                "This specialist is created in metadata-only safe mode first."
            ),
            "capabilities": [capability],
            "risk_level": "high",
            "safe_mode": True,
            "writes_code": False,
            "requires_approval_for_new_tasks": True,
        },
        "recovery_reason": "missing_required_capability",
        "missing_capability": capability,
        "safe_mode": True,
        "writes_code": False,
    }

def _existing_pending_or_approved_recovery(
    db: Session,
    *,
    capability: str,
) -> Optional[PlatformApprovalRequest]:
    approvals = (
        db.query(PlatformApprovalRequest)
        .filter(PlatformApprovalRequest.source_type == "capability_recovery")
        .filter(PlatformApprovalRequest.action_type == "create_specialist_agent")
        .filter(PlatformApprovalRequest.status.in_(["pending", "approved"]))
        .all()
    )

    for approval in approvals:
        try:
            payload = json.loads(approval.action_payload_json or "{}")
        except json.JSONDecodeError:
            continue

        if payload.get("missing_capability") == capability:
            return approval

    return None

def _approval_to_dict(approval: PlatformApprovalRequest) -> Dict[str, Any]:
    return {
        "approval_id": approval.approval_id,
        "title": approval.title,
        "status": approval.status,
        "risk_level": approval.risk_level,
        "source_type": approval.source_type,
        "source_id": approval.source_id,
        "action_type": approval.action_type,
        "action_payload": json.loads(approval.action_payload_json or "{}"),
        "created_at": approval.created_at.isoformat() if approval.created_at else None,
        "updated_at": approval.updated_at.isoformat() if approval.updated_at else None,
    }

def _log_recovery_event(
    db: Session,
    *,
    status: str,
    metadata: Dict[str, Any],
) -> None:
    event = PlatformAuditEvent(
        event_type="capability_recovery_check",
        actor_type="system",
        actor_id="capability_recovery_service",
        status=status,
        metadata_json=json.dumps(metadata, sort_keys=True),
    )
    db.add(event)
    db.commit()
