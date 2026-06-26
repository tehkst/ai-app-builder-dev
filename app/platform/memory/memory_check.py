from __future__ import annotations

from app.platform.memory.registry import all_memory_scopes, get_memory_scope, memory_scopes_for_owner
from app.platform.organization.registry import all_departments, all_teams, get_organization


REQUIRED_VISIBILITIES = {"organization", "department", "team", "agent"}


def main() -> None:
    organization = get_organization()
    departments = all_departments()
    teams = all_teams()
    memory_scopes = all_memory_scopes()

    assert memory_scopes, "memory scopes are required"

    organization_scopes = memory_scopes_for_owner("organization", organization.organization_id)
    assert organization_scopes, organization

    for department_id, department in departments.items():
        assert department.memory_scope, department
        scope = get_memory_scope(department.memory_scope)
        assert scope is not None, department
        assert scope.owner_type == "department" or scope.owner_type == "organization", scope
        if scope.owner_type == "department":
            assert scope.owner_id == department_id, scope
        assert scope.visibility in REQUIRED_VISIBILITIES, scope
        assert scope.allowed_entries, scope

    for team_id, team in teams.items():
        assert team.memory_scope, team
        scope = get_memory_scope(team.memory_scope)
        assert scope is not None, team
        assert scope.owner_type == "team", scope
        assert scope.owner_id == team_id, scope
        assert scope.visibility in REQUIRED_VISIBILITIES, scope
        assert scope.allowed_entries, scope

    print("ENGINEERING MEMORY CHECK PASSED")


if __name__ == "__main__":
    main()
