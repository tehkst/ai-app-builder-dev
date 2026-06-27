from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ProjectDefinition:
    project_id: str
    name: str
    organization_id: str
    owning_department_id: str
    team_ids: List[str]
    workflow_ids: List[str]
    memory_scope_ids: List[str]


PROJECTS: Dict[str, ProjectDefinition] = {
    "transport_lead_crm": ProjectDefinition(
        project_id="transport_lead_crm",
        name="Transport Lead CRM",
        organization_id="ai_software_factory",
        owning_department_id="backend",
        team_ids=["architecture_core", "backend_core", "database_core", "frontend_core", "quality_review", "quality_testing"],
        workflow_ids=["v100_multi_agent_workflow"],
        memory_scope_ids=[
            "organization_architecture_memory",
            "backend_department_memory",
            "database_department_memory",
            "frontend_department_memory",
            "quality_department_memory",
        ],
    ),
}


def all_projects() -> Dict[str, ProjectDefinition]:
    return dict(PROJECTS)


def get_project(project_id: str) -> Optional[ProjectDefinition]:
    return PROJECTS.get(project_id)
