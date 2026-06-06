from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.platform.agents.registry import AgentDefinition, get_agent, register_agent
from app.platform.persistence.models import PlatformApprovalRequest


SAFE_AGENT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*_agent$")
SAFE_CAPABILITY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*_task$")


def _safe_specialist_handler(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Safe V2 metadata-only handler for approved Agent Factory specialists.

    This does not write files, deploy code, call payments, or perform external actions.
    It only returns a structured plan stub proving the approved specialist agent is
    discoverable and executable through the registry.
    """
    goal = (task or {}).get("goal") or (task or {}).get("input_payload", {}).get("goal")

    return {
        "success": True,
        "safe_mode": True,
        "writes_code": False,
        "agent_id": (task or {}).get("agent_id"),
        "message": "Approved specialist agent executed in metadata-only safe mode.",
        "goal": goal,
        "next_step": "Future versions may generate executable agent code behind a separate approval gate.",
    }


def _load_payload(approval: PlatformApprovalRequest) -> Dict[str, Any]:
    try:
        return json.loads(approval.action_payload_json or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid approval payload JSON for {approval.approval_id}") from exc


def _validate_proposed_agent(proposed_agent: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(proposed_agent, dict):
        raise ValueError("proposed_agent must be an object")

    agent_id = str(proposed_agent.get("agent_id") or "").strip()
    name = str(proposed_agent.get("name") or "").strip()
    description = str(proposed_agent.get("description") or "").strip()
    capabilities = proposed_agent.get("capabilities") or []
    risk_level = str(proposed_agent.get("risk_level") or "medium").strip().lower()

    if not SAFE_AGENT_ID_PATTERN.match(agent_id):
        raise ValueError(f"Unsafe agent_id: {agent_id}")

    if not name:
        raise ValueError("Agent name is required")

    if not description:
        raise ValueError("Agent description is required")

    if risk_level not in {"low", "medium", "high", "critical"}:
        raise ValueError(f"Unsupported risk_level: {risk_level}")

    if not isinstance(capabilities, list) or not capabilities:
        raise ValueError("Agent capabilities must be a non-empty list")

    clean_capabilities: List[str] = []
    for capability in capabilities:
        capability_text = str(capability or "").strip()
        if not SAFE_CAPABILITY_PATTERN.match(capability_text):
            raise ValueError(f"Unsafe capability: {capability_text}")
        clean_capabilities.append(capability_text)

    return {
        "agent_id": agent_id,
        "name": name,
        "description": description,
        "capabilities": clean_capabilities,
        "risk_level": risk_level,
    }


def find_approved_agent_factory_requests(db: Session) -> List[PlatformApprovalRequest]:
    return (
        db.query(PlatformApprovalRequest)
        .filter(PlatformApprovalRequest.status == "approved")
        .filter(PlatformApprovalRequest.source_type == "agent_factory")
        .filter(PlatformApprovalRequest.action_type == "create_specialist_agent")
        .order_by(PlatformApprovalRequest.created_at.asc())
        .all()
    )


def register_approved_specialist_agents(db: Session) -> Dict[str, Any]:
    approvals = find_approved_agent_factory_requests(db)

    registered_agents: List[Dict[str, Any]] = []
    skipped_agents: List[Dict[str, Any]] = []
    failed_agents: List[Dict[str, Any]] = []

    for approval in approvals:
        try:
            payload = _load_payload(approval)
            proposed_agent = _validate_proposed_agent(payload.get("proposed_agent") or {})

            existing_agent = get_agent(proposed_agent["agent_id"])
            if existing_agent:
                skipped_agents.append(
                    {
                        "approval_id": approval.approval_id,
                        "agent_id": proposed_agent["agent_id"],
                        "reason": "already_registered",
                    }
                )
                continue

            def handler(task: Dict[str, Any], agent_id: str = proposed_agent["agent_id"]) -> Dict[str, Any]:
                task = dict(task or {})
                task.setdefault("agent_id", agent_id)
                return _safe_specialist_handler(task)

            register_agent(
                AgentDefinition(
                    agent_id=proposed_agent["agent_id"],
                    name=proposed_agent["name"],
                    description=proposed_agent["description"],
                    capabilities=proposed_agent["capabilities"],
                    handler=handler,
                    requires_approval_for_new_tasks=True,
                )
            )

            registered_agents.append(
                {
                    "approval_id": approval.approval_id,
                    "agent_id": proposed_agent["agent_id"],
                    "name": proposed_agent["name"],
                    "capabilities": proposed_agent["capabilities"],
                    "risk_level": proposed_agent["risk_level"],
                    "safe_mode": True,
                    "writes_code": False,
                }
            )
        except Exception as exc:
            failed_agents.append(
                {
                    "approval_id": approval.approval_id,
                    "error": str(exc),
                }
            )

    return {
        "success": len(failed_agents) == 0,
        "approved_request_count": len(approvals),
        "registered_count": len(registered_agents),
        "skipped_count": len(skipped_agents),
        "failed_count": len(failed_agents),
        "registered_agents": registered_agents,
        "skipped_agents": skipped_agents,
        "failed_agents": failed_agents,
    }
