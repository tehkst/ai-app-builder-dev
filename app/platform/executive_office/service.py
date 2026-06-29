from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from typing import Any

from app.platform.mission_control.service import build_mission_control_summary


@dataclass(frozen=True)
class ExecutiveMetric:
    name: str
    value: str
    status: str
    description: str


@dataclass(frozen=True)
class ExecutiveDecision:
    title: str
    priority: str
    recommendation: str


@dataclass(frozen=True)
class ExecutiveBriefing:
    founder: str
    company: str
    environment: str
    platform_health: str
    headline: str
    metrics: list[ExecutiveMetric]
    decisions: list[ExecutiveDecision]
    next_focus: str


def build_executive_briefing() -> dict[str, Any]:
    mission_control = build_mission_control_summary()
    founder = os.getenv("FOUNDER_NAME", "Toni")

    briefing = ExecutiveBriefing(
        founder=founder,
        company=mission_control.company,
        environment=mission_control.environment,
        platform_health=mission_control.health,
        headline="Mission Control is live and operating from GCP.",
        metrics=[
            ExecutiveMetric(
                name="Company Health",
                value=mission_control.health,
                status="healthy",
                description="The live control plane and Mission Control API are responding.",
            ),
            ExecutiveMetric(
                name="Departments Online",
                value=str(len(mission_control.departments)),
                status="healthy",
                description="Core operating departments have been registered in Mission Control.",
            ),
            ExecutiveMetric(
                name="Company DNA Principles",
                value=str(len(mission_control.principles)),
                status="healthy",
                description="Operating principles are exposed through the control plane.",
            ),
            ExecutiveMetric(
                name="Deployment Region",
                value=mission_control.region,
                status="healthy",
                description="Primary production runtime region.",
            ),
        ],
        decisions=[
            ExecutiveDecision(
                title="Continue Mission Control product buildout",
                priority="high",
                recommendation="Proceed with Executive Office, Workforce, Knowledge Vault, and Launch Center capabilities.",
            ),
            ExecutiveDecision(
                title="Keep production deployment automated",
                priority="high",
                recommendation="Use the automated Cloud Run workflow as the default release path.",
            ),
            ExecutiveDecision(
                title="Treat AI Software Factory as customer zero",
                priority="high",
                recommendation="Every new capability should first operate AI Software Factory itself before customer rollout.",
            ),
        ],
        next_focus="Build the first visual Executive Office dashboard backed by live Mission Control APIs.",
    )
    return asdict(briefing)
