from __future__ import annotations

import os

from app.platform.mission_control.models import (
    CompanyPrinciple,
    MissionControlCard,
    MissionControlDepartment,
    MissionControlSummary,
)


def build_mission_control_summary() -> MissionControlSummary:
    from app.platform.executive_intelligence.service import build_executive_intelligence_briefing

    executive = build_executive_intelligence_briefing()
    environment = os.getenv("ENVIRONMENT", "production")
    region = os.getenv("GCP_REGION", "asia-southeast1")
    version = os.getenv("PLATFORM_VERSION", "0.1.0")

    health_value = (executive.get("platform_health") or {}).get("value") or {}
    observed_health = str(health_value.get("status") or "unknown")
    health = observed_health if observed_health in {"healthy", "degraded", "critical"} else "unknown"
    mission = (executive.get("active_mission") or {}).get("value") or {}
    next_action = (executive.get("next_recommended_action") or {}).get("value") or "No evidence-backed next action is available."
    return MissionControlSummary(
        company="AI Software Factory",
        product="Mission Control",
        environment=environment,
        region=region,
        version=version,
        health=health,
        cards=[
            MissionControlCard(
                title="Company Health",
                value=health,
                status=health,
                description="Derived from the canonical Executive Intelligence health evidence.",
            ),
            MissionControlCard(
                title="Active Mission",
                value=str(mission.get("title") or mission.get("mission_id") or "unknown"),
                status=health,
                description="Derived from the current durable Mission Pipeline projection.",
            ),
            MissionControlCard(
                title="Deployment",
                value=str((executive.get("deployed_revision") or {}).get("value") or "unknown"),
                status=health,
                description="Observed Cloud Run revision, or unknown when runtime evidence is unavailable.",
            ),
            MissionControlCard(
                title="Cloud Region",
                value=region,
                status=health,
                description="Primary production region for the control plane.",
            ),
        ],
        departments=[
            MissionControlDepartment(
                name="Executive Office",
                capability="Company command, strategy, and founder decisions",
                status=health,
                active_work=str(next_action),
            ),
            MissionControlDepartment(
                name="Engineering Command",
                capability="Architecture, implementation, validation, and releases",
                status=health,
                active_work=str(next_action),
            ),
            MissionControlDepartment(
                name="AI Workforce",
                capability="AI employee roles, reporting lines, KPIs, and performance",
                status=health,
                active_work=str(next_action),
            ),
            MissionControlDepartment(
                name="Knowledge Vault",
                capability="Institutional memory, decisions, runbooks, and lessons learned",
                status=health,
                active_work=str(next_action),
            ),
            MissionControlDepartment(
                name="Launch Center",
                capability="Deployments, environments, releases, rollback, and live status",
                status=health,
                active_work=str(next_action),
            ),
            MissionControlDepartment(
                name="Finance",
                capability="Cloud cost, AI cost, budgets, revenue, and margins",
                status=health,
                active_work=str(next_action),
            ),
        ],
        principles=[
            CompanyPrinciple(
                category="Engineering DNA",
                principle="Small, production-safe pull requests with validation before deploy.",
                enforcement="Repository gates and deployment workflow checks.",
            ),
            CompanyPrinciple(
                category="Product DNA",
                principle="Build company capabilities, not disconnected features.",
                enforcement="Mission Control bounded-context roadmap.",
            ),
            CompanyPrinciple(
                category="Operating DNA",
                principle="AI Software Factory is customer zero and must run itself first.",
                enforcement="Dogfood Mission Control before generalizing to customers.",
            ),
        ],
    )
