from __future__ import annotations

from typing import Dict, List, Optional

from app.platform.management.models import DelegationRule, ManagementRole


MANAGEMENT_ROLES: Dict[str, ManagementRole] = {
    "ceo": ManagementRole(
        role_id="ceo",
        title="CEO Agent",
        level="executive",
        agent_id="ceo_agent",
        delegates_to=["cto"],
        responsibilities=["business strategy", "product prioritization", "resource allocation"],
    ),
    "cto": ManagementRole(
        role_id="cto",
        title="CTO Agent",
        level="executive",
        agent_id="cto_agent",
        delegates_to=["engineering_manager"],
        responsibilities=["technical strategy", "platform architecture", "engineering standards"],
    ),
    "engineering_manager": ManagementRole(
        role_id="engineering_manager",
        title="Engineering Manager Agent",
        level="engineering_leadership",
        agent_id="engineering_manager_agent",
        delegates_to=["backend_manager", "frontend_manager", "database_manager", "quality_manager"],
        responsibilities=["task assignment", "workflow coordination", "bottleneck detection"],
    ),
    "backend_manager": ManagementRole(
        role_id="backend_manager",
        title="Backend Manager Agent",
        level="department_management",
        agent_id="backend_manager_agent",
        delegates_to=["backend_builder_agent"],
        responsibilities=["backend delegation", "service ownership", "API delivery"],
    ),
    "frontend_manager": ManagementRole(
        role_id="frontend_manager",
        title="Frontend Manager Agent",
        level="department_management",
        agent_id="frontend_manager_agent",
        delegates_to=["frontend_builder_agent"],
        responsibilities=["frontend delegation", "UI delivery", "client interaction quality"],
    ),
    "database_manager": ManagementRole(
        role_id="database_manager",
        title="Database Manager Agent",
        level="department_management",
        agent_id="database_manager_agent",
        delegates_to=["database_builder_agent"],
        responsibilities=["database delegation", "schema ownership", "data model quality"],
    ),
    "quality_manager": ManagementRole(
        role_id="quality_manager",
        title="Quality Manager Agent",
        level="department_management",
        agent_id="quality_manager_agent",
        delegates_to=["reviewer_agent", "test_agent", "code_steward_agent"],
        responsibilities=["review delegation", "testing coordination", "modularity governance"],
    ),
}


DELEGATION_RULES: Dict[str, DelegationRule] = {
    "ceo_to_cto": DelegationRule("ceo_to_cto", "ceo", "cto", "technical_strategy", True),
    "cto_to_eng": DelegationRule("cto_to_eng", "cto", "engineering_manager", "engineering_execution", True),
    "eng_to_backend": DelegationRule("eng_to_backend", "engineering_manager", "backend_manager", "backend", True),
    "eng_to_frontend": DelegationRule("eng_to_frontend", "engineering_manager", "frontend_manager", "frontend", True),
    "eng_to_database": DelegationRule("eng_to_database", "engineering_manager", "database_manager", "database", True),
    "eng_to_quality": DelegationRule("eng_to_quality", "engineering_manager", "quality_manager", "quality", True),
}


def all_management_roles() -> Dict[str, ManagementRole]:
    return dict(MANAGEMENT_ROLES)


def all_delegation_rules() -> Dict[str, DelegationRule]:
    return dict(DELEGATION_RULES)


def get_management_role(role_id: str) -> Optional[ManagementRole]:
    return MANAGEMENT_ROLES.get(role_id)


def roles_for_agent(agent_id: str) -> List[ManagementRole]:
    return [role for role in MANAGEMENT_ROLES.values() if role.agent_id == agent_id]
