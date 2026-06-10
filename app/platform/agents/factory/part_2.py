# Split from the legacy module to keep each Python file under 200 lines.
from __future__ import annotations
import re
from typing import Any, Dict, List, Optional
import json
import uuid
from app.platform.persistence.database import PlatformSessionLocal
from app.platform.persistence.models import PlatformApprovalRequest
from app.platform.services.approval_service import approval_to_dict
from app.platform.services.telegram_approval_service import (
    TelegramApprovalSendError,
    send_approval_to_telegram,
)
KNOWN_AGENT_CAPABILITIES = {
    "architect_task",
    "builder_task",
    "reviewer_task",
    "test_task",
    "orchestrator_task",
    "plan_project",
    "agent_orchestration",
    "worker_loop_test",
}
DOMAIN_AGENT_HINTS = {
    "route": {
        "agent_id": "route_optimization_agent",
        "name": "Route Optimization Agent",
        "description": "Plans route optimization logic for transport and logistics applications.",
        "capabilities": ["route_optimization_task"],
        "risk_level": "medium",
    },
    "transport": {
        "agent_id": "transport_domain_agent",
        "name": "Transport Domain Agent",
        "description": "Plans transport-specific modules such as trips, vehicles, drivers, routes, attendance, and dispatch.",
        "capabilities": ["transport_domain_task"],
        "risk_level": "medium",
    },
    "payment": {
        "agent_id": "payment_integration_agent",
        "name": "Payment Integration Agent",
        "description": "Plans payment integration requirements, safety checks, and approval requirements.",
        "capabilities": ["payment_integration_task"],
        "risk_level": "high",
    },
    "notification": {
        "agent_id": "notification_agent",
        "name": "Notification Agent",
        "description": "Plans notification flows such as email, SMS, push notifications, and Telegram alerts.",
        "capabilities": ["notification_task"],
        "risk_level": "medium",
    },
    "report": {
        "agent_id": "reporting_agent",
        "name": "Reporting Agent",
        "description": "Plans reports, dashboards, KPIs, and analytics modules.",
        "capabilities": ["reporting_task"],
        "risk_level": "low",
    },
    "dashboard": {
        "agent_id": "dashboard_agent",
        "name": "Dashboard Agent",
        "description": "Plans admin dashboards, metrics screens, and management views.",
        "capabilities": ["dashboard_task"],
        "risk_level": "low",
    },
}

def agent_factory_handler(task: Dict[str, Any]) -> Dict[str, Any]:
    input_payload = task.get("input_payload") or {}
    goal = str(input_payload.get("goal") or task.get("description") or task.get("title") or "")

    proposed_agents = infer_needed_agents(goal)
    parent_task_id = input_payload.get("parent_task_id")
    approval_requests: List[Dict[str, Any]] = []
    telegram_send_results: List[Dict[str, Any]] = []

    db = PlatformSessionLocal()
    try:
        for proposed_agent in proposed_agents:
            if not proposed_agent.get("approval_required"):
                continue

            approval = PlatformApprovalRequest(
                approval_id=f"approval_{uuid.uuid4().hex}",
                title=f"Approve new specialist agent: {proposed_agent.get('name')}",
                description=proposed_agent.get("description"),
                status="pending",
                risk_level=proposed_agent.get("risk_level", "medium"),
                requested_by="agent_factory_agent",
                source_type="agent_factory",
                source_id=parent_task_id or task.get("task_id"),
                action_type="create_specialist_agent",
                action_payload_json=json.dumps(
                    build_agent_creation_approval_payload(
                        proposed_agent=proposed_agent,
                        goal=goal,
                        parent_task_id=parent_task_id,
                    )
                ),
                tenant_id=task.get("tenant_id"),
                workspace_id=task.get("workspace_id"),
                project_id=task.get("project_id"),
                chat_channel="telegram",
            )

            db.add(approval)
            db.commit()
            db.refresh(approval)
            approval_data = approval_to_dict(approval)
            approval_requests.append(approval_data)

            try:
                telegram_result = send_approval_to_telegram(
                    db=db,
                    approval_id=approval.approval_id,
                )
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
    finally:
        db.close()

    return {
        "success": True,
        "agent_id": "agent_factory_agent",
        "message": "Agent Factory Agent V1 proposed specialist agent specifications.",
        "goal": goal,
        "proposed_agent_count": len(proposed_agents),
        "proposed_agents": proposed_agents,
        "approval_request_count": len(approval_requests),
        "approval_requests": approval_requests,
        "telegram_send_results": telegram_send_results,
        "safe_mode": True,
        "writes_code": False,
        "reason": "V1 only proposes new agents and creates approval requests. Creating executable agent code will require approval in a later version.",
    }
