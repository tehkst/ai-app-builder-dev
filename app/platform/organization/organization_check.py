from __future__ import annotations

import app.platform.agents.specialists  # noqa: F401 - registers specialist agents

from app.platform.agents.manifest_registry import get_manifest
from app.platform.agents.registry import get_agent
from app.platform.organization.registry import all_departments, all_teams, departments_for_agent, get_organization, teams_for_department


REQUIRED_DEPARTMENTS = {"architecture", "backend", "database", "frontend", "quality"}
REQUIRED_TEAMS = {"architecture_core", "backend_core", "database_core", "frontend_core", "quality_review", "quality_testing"}


def main() -> None:
    organization = get_organization()
    departments = all_departments()
    teams = all_teams()

    assert organization.organization_id == "ai_software_factory", organization
    assert REQUIRED_DEPARTMENTS.issubset(set(organization.department_ids)), organization
    assert REQUIRED_DEPARTMENTS.issubset(set(departments)), departments
    assert REQUIRED_TEAMS.issubset(set(teams)), teams

    for department_id in organization.department_ids:
        department = departments.get(department_id)
        assert department is not None, department_id
        assert department.department_id == department_id, department
        assert department.lead_agent_id, department
        assert get_agent(department.lead_agent_id) is not None, department
        assert get_manifest(department.lead_agent_id) is not None, department
        assert department.memory_scope, department
        assert department.responsibilities, department
        assert teams_for_department(department_id), department

    for team_id, team in teams.items():
        assert team.team_id == team_id, team
        assert team.department_id in departments, team
        assert team.lead_agent_id in team.member_agent_ids, team
        assert get_agent(team.lead_agent_id) is not None, team
        assert get_manifest(team.lead_agent_id) is not None, team
        assert team.memory_scope, team
        assert team.responsibilities, team
        for agent_id in team.member_agent_ids:
            assert get_agent(agent_id) is not None, {"team_id": team_id, "agent_id": agent_id}
            assert get_manifest(agent_id) is not None, {"team_id": team_id, "agent_id": agent_id}

    for agent_id in ["architect_agent", "backend_builder_agent", "database_builder_agent", "frontend_builder_agent", "reviewer_agent", "test_agent"]:
        assert departments_for_agent(agent_id), agent_id

    print("ORGANIZATION HIERARCHY CHECK PASSED")


if __name__ == "__main__":
    main()
