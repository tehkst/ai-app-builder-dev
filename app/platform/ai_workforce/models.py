from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkforceKPI:
    name: str
    target: str
    current: str
    status: str


@dataclass(frozen=True)
class AIEmployee:
    employee_id: str
    name: str
    role: str
    department: str
    manager: str
    mission: str
    status: str
    skills: list[str]
    kpis: list[WorkforceKPI]


@dataclass(frozen=True)
class WorkforceSummary:
    company: str
    product: str
    operating_model: str
    total_employees: int
    active_employees: int
    departments: list[str]
    employees: list[AIEmployee]
