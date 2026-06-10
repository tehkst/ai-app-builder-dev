# Split from the legacy module to keep each Python file under 200 lines.
from __future__ import annotations
import json
import re
from typing import Any, Dict, List
from sqlalchemy.orm import Session
from app.platform.agents.registry import AgentDefinition, get_agent, register_agent
from app.platform.persistence.models import PlatformAgentDefinition, PlatformApprovalRequest, utc_now
SAFE_AGENT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*_agent$")
SAFE_CAPABILITY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*_task$")

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
            existing_db_agent = (
                db.query(PlatformAgentDefinition)
                .filter(PlatformAgentDefinition.agent_id == proposed_agent["agent_id"])
                .first()
            )

            if existing_agent and existing_db_agent:
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

            if existing_db_agent is None:
                db_agent = PlatformAgentDefinition(
                    agent_id=proposed_agent["agent_id"],
                    name=proposed_agent["name"],
                    description=proposed_agent["description"],
                    capabilities_json=json.dumps(proposed_agent["capabilities"], sort_keys=True),
                    risk_level=proposed_agent["risk_level"],
                    status="active",
                    source_approval_id=approval.approval_id,
                    source_type="agent_factory",
                    safe_mode=True,
                    writes_code=False,
                    requires_approval_for_new_tasks=True,
                    metadata_json=json.dumps(
                        {
                            "registered_by": "agent_factory_registration_service",
                            "registration_mode": "metadata_only",
                        },
                        sort_keys=True,
                    ),
                )
                db.add(db_agent)
            else:
                existing_db_agent.name = proposed_agent["name"]
                existing_db_agent.description = proposed_agent["description"]
                existing_db_agent.capabilities_json = json.dumps(
                    proposed_agent["capabilities"],
                    sort_keys=True,
                )
                existing_db_agent.risk_level = proposed_agent["risk_level"]
                existing_db_agent.status = "active"
                existing_db_agent.safe_mode = True
                existing_db_agent.writes_code = False
                existing_db_agent.requires_approval_for_new_tasks = True
                existing_db_agent.updated_at = utc_now()

            db.commit()

            registered_agents.append(
                {
                    "approval_id": approval.approval_id,
                    "agent_id": proposed_agent["agent_id"],
                    "name": proposed_agent["name"],
                    "capabilities": proposed_agent["capabilities"],
                    "risk_level": proposed_agent["risk_level"],
                    "safe_mode": True,
                    "writes_code": False,
                    "persisted": True,
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
