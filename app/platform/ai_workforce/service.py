from __future__ import annotations

from dataclasses import asdict
from typing import Any

from app.platform.ai_workforce.models import AIEmployee, WorkforceKPI, WorkforceSummary


def _kpi(name: str, target: str, current: str) -> WorkforceKPI:
    return WorkforceKPI(name=name, target=target, current=current, status="healthy")


def build_workforce_summary() -> dict[str, Any]:
    employees = [
        AIEmployee("exec-001", "Mission Control CEO", "Chief Executive", "Executive Office", "Founder", "Coordinate company priorities.", "active", ["strategy", "company health"], [_kpi("Company health", "healthy", "healthy")]),
        AIEmployee("eng-001", "Engineering Lead", "VP Engineering", "Engineering Command", "Mission Control CEO", "Turn priorities into production software.", "active", ["architecture", "deployment"], [_kpi("Deployment success", "100%", "100%")]),
        AIEmployee("launch-001", "Launch Engineer", "DevOps", "Launch Center", "Engineering Lead", "Operate releases and verification.", "active", ["GCP", "Cloud Run"], [_kpi("Release time", "under 5 minutes", "under 3 minutes")]),
        AIEmployee("knowledge-001", "Knowledge Curator", "Knowledge Vault", "Knowledge Vault", "Mission Control CEO", "Preserve company memory.", "active", ["documentation", "memory"], [_kpi("Decision capture", "complete", "in progress")]),
        AIEmployee("finance-001", "Cost Controller", "Finance", "Finance", "Mission Control CEO", "Track cost, budgets, and margin readiness.", "active", ["cost controls", "budgeting"], [_kpi("Cost gate", "enabled", "enabled")]),
    ]
    departments = sorted({employee.department for employee in employees})
    return asdict(WorkforceSummary("AI Software Factory", "AI Workforce", "Employees with roles, managers, missions, skills, and KPIs", len(employees), len(employees), departments, employees))
