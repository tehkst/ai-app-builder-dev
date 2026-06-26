from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class TeamDefinition:
    team_id: str
    name: str
    department_id: str
    lead_agent_id: str
    member_agent_ids: List[str]
    responsibilities: List[str]
    memory_scope: str


@dataclass(frozen=True)
class DepartmentDefinition:
    department_id: str
    name: str
    lead_agent_id: str
    team_ids: List[str]
    responsibilities: List[str]
    memory_scope: str


@dataclass(frozen=True)
class OrganizationDefinition:
    organization_id: str
    name: str
    department_ids: List[str]
    operating_principles: List[str]


ORGANIZATION = OrganizationDefinition(
    organization_id="ai_software_factory",
    name="AI Software Factory",
    department_ids=["architecture", "backend", "database", "frontend", "quality"],
    operating_principles=[
        "Scope before build.",
        "Every capability is declared through manifests and contracts.",
        "Departments own domain responsibilities, memory, and quality gates.",
        "Agents interact through explicit inputs, outputs, capabilities, and metadata.",
        "No materialization or deployment occurs without approval.",
    ],
)


DEPARTMENTS: Dict[str, DepartmentDefinition] = {
    "architecture": DepartmentDefinition(
        department_id="architecture",
        name="Architecture Department",
        lead_agent_id="architect_agent",
        team_ids=["architecture_core"],
        responsibilities=["system design", "scope interpretation", "technical planning"],
        memory_scope="organization_architecture_memory",
    ),
    "backend": DepartmentDefinition(
        department_id="backend",
        name="Backend Department",
        lead_agent_id="backend_builder_agent",
        team_ids=["backend_core"],
        responsibilities=["services", "routes", "business logic", "backend tests"],
        memory_scope="backend_department_memory",
    ),
    "database": DepartmentDefinition(
        department_id="database",
        name="Database Department",
        lead_agent_id="database_builder_agent",
        team_ids=["database_core"],
        responsibilities=["data models", "schemas", "relationships", "persistence"],
        memory_scope="database_department_memory",
    ),
    "frontend": DepartmentDefinition(
        department_id="frontend",
        name="Frontend Department",
        lead_agent_id="frontend_builder_agent",
        team_ids=["frontend_core"],
        responsibilities=["ui shell", "components", "forms", "client interaction"],
        memory_scope="frontend_department_memory",
    ),
    "quality": DepartmentDefinition(
        department_id="quality",
        name="Quality Department",
        lead_agent_id="reviewer_agent",
        team_ids=["quality_review", "quality_testing"],
        responsibilities=["review", "testing", "release readiness", "regression protection"],
        memory_scope="quality_department_memory",
    ),
}


TEAMS: Dict[str, TeamDefinition] = {
    "architecture_core": TeamDefinition(
        team_id="architecture_core",
        name="Architecture Core Team",
        department_id="architecture",
        lead_agent_id="architect_agent",
        member_agent_ids=["architect_agent"],
        responsibilities=["architecture plans", "scope-to-technical translation"],
        memory_scope="architecture_team_memory",
    ),
    "backend_core": TeamDefinition(
        team_id="backend_core",
        name="Backend Core Team",
        department_id="backend",
        lead_agent_id="backend_builder_agent",
        member_agent_ids=["backend_builder_agent"],
        responsibilities=["backend previews", "service and route contracts"],
        memory_scope="backend_team_memory",
    ),
    "database_core": TeamDefinition(
        team_id="database_core",
        name="Database Core Team",
        department_id="database",
        lead_agent_id="database_builder_agent",
        member_agent_ids=["database_builder_agent"],
        responsibilities=["database previews", "model and schema contracts"],
        memory_scope="database_team_memory",
    ),
    "frontend_core": TeamDefinition(
        team_id="frontend_core",
        name="Frontend Core Team",
        department_id="frontend",
        lead_agent_id="frontend_builder_agent",
        member_agent_ids=["frontend_builder_agent"],
        responsibilities=["frontend previews", "UI shell contracts"],
        memory_scope="frontend_team_memory",
    ),
    "quality_review": TeamDefinition(
        team_id="quality_review",
        name="Quality Review Team",
        department_id="quality",
        lead_agent_id="reviewer_agent",
        member_agent_ids=["reviewer_agent"],
        responsibilities=["review checklists", "quality gates"],
        memory_scope="quality_review_team_memory",
    ),
    "quality_testing": TeamDefinition(
        team_id="quality_testing",
        name="Quality Testing Team",
        department_id="quality",
        lead_agent_id="test_agent",
        member_agent_ids=["test_agent"],
        responsibilities=["test plans", "release readiness validation"],
        memory_scope="quality_testing_team_memory",
    ),
}


def get_organization() -> OrganizationDefinition:
    return ORGANIZATION


def all_departments() -> Dict[str, DepartmentDefinition]:
    return dict(DEPARTMENTS)


def all_teams() -> Dict[str, TeamDefinition]:
    return dict(TEAMS)


def get_department(department_id: str) -> Optional[DepartmentDefinition]:
    return DEPARTMENTS.get(department_id)


def get_team(team_id: str) -> Optional[TeamDefinition]:
    return TEAMS.get(team_id)


def teams_for_department(department_id: str) -> List[TeamDefinition]:
    department = get_department(department_id)
    if department is None:
        return []
    return [TEAMS[team_id] for team_id in department.team_ids if team_id in TEAMS]


def departments_for_agent(agent_id: str) -> List[DepartmentDefinition]:
    result = []
    for department in DEPARTMENTS.values():
        if department.lead_agent_id == agent_id:
            result.append(department)
            continue
        for team in teams_for_department(department.department_id):
            if agent_id in team.member_agent_ids:
                result.append(department)
                break
    return result
