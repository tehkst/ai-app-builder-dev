from __future__ import annotations

import app.platform.agents.specialists  # noqa: F401

from app.platform.agents.manifest_registry import get_manifest
from app.platform.agents.registry import get_agent
from app.platform.management.models import MANAGEMENT_LEVELS
from app.platform.management.registry import all_delegation_rules, all_management_roles


REQUIRED_ROLES = {
    "ceo",
    "cto",
    "engineering_manager",
    "backend_manager",
    "frontend_manager",
    "database_manager",
    "quality_manager",
}


def main() -> None:
    roles = all_management_roles()
    rules = all_delegation_rules()

    assert REQUIRED_ROLES.issubset(set(roles)), roles
    assert rules, "delegation rules are required"

    for role_id, role in roles.items():
        assert role.role_id == role_id, role
        assert role.level in MANAGEMENT_LEVELS, role
        assert role.agent_id, role
        assert get_agent(role.agent_id) is not None, role
        assert get_manifest(role.agent_id) is not None, role
        assert role.responsibilities, role

        for target in role.delegates_to:
            if target in roles:
                continue
            assert get_agent(target) is not None, {"role": role_id, "target": target}

    for rule in rules.values():
        assert rule.from_role_id in roles, rule
        assert rule.to_role_id in roles, rule
        assert rule.allowed is True, rule

    print("ENGINEERING MANAGEMENT CHECK PASSED")


if __name__ == "__main__":
    main()
