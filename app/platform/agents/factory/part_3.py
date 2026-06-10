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

def build_agent_creation_approval_payload(
    proposed_agent: Dict[str, Any],
    goal: str,
    parent_task_id: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "goal": goal,
        "parent_task_id": parent_task_id,
        "proposed_agent": proposed_agent,
        "safe_mode": True,
        "writes_code": False,
        "next_step": "Human approval required before creating executable agent code.",
    }
