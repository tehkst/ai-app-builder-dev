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

def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value.lower()).strip("_")
    return cleaned or "custom"

def infer_needed_agents(goal: str) -> List[Dict[str, Any]]:
    lower_goal = goal.lower()
    proposed_agents: List[Dict[str, Any]] = []
    seen_agent_ids = set()

    for keyword, spec in DOMAIN_AGENT_HINTS.items():
        if keyword in lower_goal and spec["agent_id"] not in seen_agent_ids:
            proposed_agents.append(
                {
                    **spec,
                    "matched_keyword": keyword,
                    "approval_required": spec.get("risk_level") in {"high", "critical"},
                    "status": "proposed",
                }
            )
            seen_agent_ids.add(spec["agent_id"])

    if not proposed_agents and goal.strip():
        slug = _slug(goal[:40])
        proposed_agents.append(
            {
                "agent_id": f"{slug}_agent",
                "name": f"{goal[:40].strip()} Agent",
                "description": f"Proposed custom specialist agent for: {goal}",
                "capabilities": [f"{slug}_task"],
                "risk_level": "medium",
                "approval_required": True,
                "matched_keyword": "custom",
                "status": "proposed",
            }
        )

    return proposed_agents
