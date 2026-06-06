from __future__ import annotations

import json
import re
import uuid
from typing import Any, Dict, List

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
) -> PlatformApprovalRequest | None:
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


def create_recovery_approvals_for_missing_capabilities(
    db: Session,
    *,
    required_capabilities: List[str],
    create_approvals: bool = True,
    send_telegram: bool = False,
    log_event: bool = True,
) -> Dict[str, Any]:
    graph = build_agent_dependency_graph(
        db,
        required_capabilities=required_capabilities,
        log_event=False,
    )

    missing_capabilities = graph.get("missing_capabilities", [])

    created_approvals: List[Dict[str, Any]] = []
    telegram_send_results: List[Dict[str, Any]] = []
    skipped_capabilities: List[Dict[str, Any]] = []
    invalid_capabilities: List[Dict[str, Any]] = []

    for capability in missing_capabilities:
        if not _CAPABILITY_PATTERN.match(capability):
            invalid_capabilities.append(
                {
                    "capability": capability,
                    "reason": "invalid_capability_name",
                }
            )
            continue

        existing = _existing_pending_or_approved_recovery(db, capability=capability)
        if existing:
            skipped_capabilities.append(
                {
                    "capability": capability,
                    "reason": "existing_pending_or_approved_recovery",
                    "approval_id": existing.approval_id,
                    "status": existing.status,
                }
            )
            continue

        payload = _create_agent_factory_payload(capability)

        if not create_approvals:
            skipped_capabilities.append(
                {
                    "capability": capability,
                    "reason": "dry_run",
                    "proposed_agent": payload["proposed_agent"],
                }
            )
            continue

        approval = PlatformApprovalRequest(
            approval_id=f"approval_{uuid.uuid4().hex}",
            title=f"Create {_agent_name_from_capability(capability)}",
            description=(
                f"Capability recovery detected missing required capability '{capability}'. "
                "Approve this request to allow Agent Factory to register a safe metadata-only specialist."
            ),
            status="pending",
            risk_level="high",
            requested_by="capability_recovery_service",
            source_type="capability_recovery",
            source_id=capability,
            action_type="create_specialist_agent",
            action_payload_json=json.dumps(payload, sort_keys=True),
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(approval)
        db.commit()

        approval_data = _approval_to_dict(approval)

        if send_telegram:
            try:
                telegram_result = send_approval_to_telegram(db, approval.approval_id)
                telegram_send_results.append(
                    {
                        "approval_id": approval.approval_id,
                        "sent": True,
                        "telegram": telegram_result.get("telegram"),
                    }
                )
            except TelegramApprovalSendError as exc:
                telegram_send_results.append(
                    {
                        "approval_id": approval.approval_id,
                        "sent": False,
                        "error": str(exc),
                    }
                )

        created_approvals.append(approval_data)

    status = "healthy"
    if invalid_capabilities:
        status = "invalid_missing_capabilities"
    elif created_approvals:
        status = "recovery_approval_created"
    elif skipped_capabilities:
        status = "recovery_approval_skipped"
    elif missing_capabilities:
        status = "missing_capabilities_no_action"

    result = {
        "success": status in {
            "healthy",
            "recovery_approval_created",
            "recovery_approval_skipped",
        },
        "status": status,
        "create_approvals": create_approvals,
        "send_telegram": send_telegram,
        "required_capabilities": required_capabilities,
        "missing_capabilities": missing_capabilities,
        "missing_capability_count": len(missing_capabilities),
        "created_approvals": created_approvals,
        "created_approval_count": len(created_approvals),
        "telegram_send_results": telegram_send_results,
        "telegram_send_count": len([item for item in telegram_send_results if item.get("sent")]),
        "telegram_error_count": len([item for item in telegram_send_results if not item.get("sent")]),
        "skipped_capabilities": skipped_capabilities,
        "skipped_count": len(skipped_capabilities),
        "invalid_capabilities": invalid_capabilities,
        "invalid_count": len(invalid_capabilities),
        "dependency_graph_status": graph.get("status"),
        "dependency_repair_plan": graph.get("repair_plan", []),
    }

    if log_event:
        _log_recovery_event(
            db,
            status=status,
            metadata={
                "missing_capability_count": result["missing_capability_count"],
                "created_approval_count": result["created_approval_count"],
                "skipped_count": result["skipped_count"],
                "invalid_count": result["invalid_count"],
                "create_approvals": create_approvals,
                "send_telegram": send_telegram,
                "telegram_send_count": result["telegram_send_count"],
                "telegram_error_count": result["telegram_error_count"],
        "send_telegram": send_telegram,
            },
        )

    return result
