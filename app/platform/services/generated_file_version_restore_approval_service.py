from __future__ import annotations

import json
from typing import Any, Dict
from uuid import uuid4

from sqlalchemy.orm import Session

from app.platform.persistence.models import PlatformApprovalRequest
from app.platform.services.generated_file_version_restore_plan_service import (
    create_generated_file_version_restore_plan,
)


def _approval_to_dict(record: PlatformApprovalRequest) -> Dict[str, Any]:
    return {
        "approval_id": record.approval_id,
        "title": record.title,
        "description": record.description,
        "status": record.status,
        "risk_level": record.risk_level,
        "requested_by": record.requested_by,
        "approver_id": record.approver_id,
        "source_type": record.source_type,
        "source_id": record.source_id,
        "action_type": record.action_type,
        "action_payload": json.loads(record.action_payload_json or "{}"),
        "decision_note": record.decision_note,
        "tenant_id": record.tenant_id,
        "workspace_id": record.workspace_id,
        "project_id": record.project_id,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        "decided_at": record.decided_at.isoformat() if record.decided_at else None,
    }


def create_generated_file_version_restore_approval_request(
    db: Session,
    target_version_id: str,
    requested_by: str = "ai_agent",
) -> Dict[str, Any]:
    restore_plan_result = create_generated_file_version_restore_plan(
        db,
        target_version_id=target_version_id,
    )

    if not restore_plan_result.get("found"):
        return {
            "success": True,
            "found": False,
            "target_version_id": target_version_id,
            "approval_created": False,
            "restore_mode": "approval_only",
            "write_mode": "db_preview_only",
            "disk_write_performed": False,
            "db_content_mutation_performed": False,
            "restore_execution_performed": False,
            "approval_request": None,
            "restore_plan": restore_plan_result.get("restore_plan"),
        }

    restore_plan = restore_plan_result.get("restore_plan") or {}
    target_version = restore_plan.get("target_version") or {}
    current_file = restore_plan.get("current_file") or {}

    action_payload = {
        "target_version_id": target_version_id,
        "generated_file_id": restore_plan_result.get("generated_file_id"),
        "restore_plan": restore_plan,
        "approval_mode": "approval_only",
        "execution_supported": False,
        "restore_execution_performed": False,
        "disk_write_performed": False,
        "db_content_mutation_performed": False,
    }

    approval = PlatformApprovalRequest(
        approval_id=f"restore_approval_{uuid4().hex}",
        title=(
            "Approve generated file restore plan for "
            + str(current_file.get("path") or "unknown file")
        ),
        description=(
            "Approval request for a plan-only generated-file restore to version "
            + str(target_version.get("version_number") or "unknown")
            + ". This approval request does not execute restore."
        ),
        status="pending",
        risk_level="high",
        requested_by=requested_by,
        source_type="generated_file_version_restore_plan",
        source_id=target_version_id,
        action_type="approve_restore_plan_only",
        action_payload_json=json.dumps(action_payload, sort_keys=True),
        workspace_id=current_file.get("workspace_id"),
        project_id=current_file.get("project_id"),
    )

    db.add(approval)
    db.commit()
    db.refresh(approval)

    return {
        "success": True,
        "found": True,
        "approval_created": True,
        "approval_id": approval.approval_id,
        "target_version_id": target_version_id,
        "generated_file_id": restore_plan_result.get("generated_file_id"),
        "restore_mode": "approval_only",
        "write_mode": "db_preview_only",
        "disk_write_performed": False,
        "db_content_mutation_performed": False,
        "restore_execution_performed": False,
        "approval_request": _approval_to_dict(approval),
        "restore_plan": restore_plan,
    }


def get_generated_file_version_restore_approval_request(
    db: Session,
    approval_id: str,
) -> Dict[str, Any]:
    approval = (
        db.query(PlatformApprovalRequest)
        .filter(PlatformApprovalRequest.approval_id == approval_id)
        .first()
    )

    if not approval:
        return {
            "success": True,
            "found": False,
            "approval_id": approval_id,
            "restore_mode": "approval_only",
            "write_mode": "db_preview_only",
            "disk_write_performed": False,
            "db_content_mutation_performed": False,
            "restore_execution_performed": False,
            "approval_request": None,
        }

    return {
        "success": True,
        "found": True,
        "approval_id": approval_id,
        "restore_mode": "approval_only",
        "write_mode": "db_preview_only",
        "disk_write_performed": False,
        "db_content_mutation_performed": False,
        "restore_execution_performed": False,
        "approval_request": _approval_to_dict(approval),
    }
