from __future__ import annotations

import os

from app.platform.mission_control.models import (
    CompanyPrinciple,
    MissionControlCard,
    MissionControlDepartment,
    MissionControlSummary,
)


def build_mission_control_summary() -> MissionControlSummary:
    environment = os.getenv("ENVIRONMENT", "production")
    region = os.getenv("GCP_REGION", "asia-southeast1")
    version = os.getenv("PLATFORM_VERSION", "0.1.0")

    return MissionControlSummary(
        company="AI Software Factory",
        product="Mission Control",
        environment=environment,
        region=region,
        version=version,
        health="healthy",
        cards=[
            MissionControlCard(
                title="Company Health",
                value="healthy",
                status="healthy",
                description="The live control plane is responding.",
            ),
            MissionControlCard(
                title="Operating Model",
                value="autonomous software company",
                status="healthy",
                description="Departments and AI employees are organized around company capabilities.",
            ),
            MissionControlCard(
                title="Deployment",
                value=environment,
                status="healthy",
                description="Mission Control is deployed through the production pipeline.",
            ),
            MissionControlCard(
                title="Cloud Region",
                value=region,
                status="healthy",
                description="Primary production region for the control plane.",
            ),
        ],
        departments=[
            MissionControlDepartment(
                name="Executive Office",
                capability="Company command, strategy, and founder decisions",
                status="healthy",
                active_work="Mission Control foundation",
            ),
            MissionControlDepartment(
                name="Engineering Command",
                capability="Architecture, implementation, validation, and releases",
                status="healthy",
                active_work="Production deployment hardening",
            ),
            MissionControlDepartment(
                name="AI Workforce",
                capability="AI employee roles, reporting lines, KPIs, and performance",
                status="healthy",
                active_work="Workforce model design",
            ),
            MissionControlDepartment(
                name="Knowledge Vault",
                capability="Institutional memory, decisions, runbooks, and lessons learned",
                status="healthy",
                active_work="Company constitution integration",
            ),
            MissionControlDepartment(
                name="Launch Center",
                capability="Deployments, environments, releases, rollback, and live status",
                status="healthy",
                active_work="Cloud Run launch validation",
            ),
            MissionControlDepartment(
                name="Finance",
                capability="Cloud cost, AI cost, budgets, revenue, and margins",
                status="healthy",
                active_work="Cost gate enforcement",
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
