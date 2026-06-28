from __future__ import annotations

from typing import Dict, List


PLATFORM_OWNER = "platform_owner"
PLATFORM_ADMIN = "platform_admin"
ORGANIZATION_OWNER = "organization_owner"
ORGANIZATION_ADMIN = "organization_admin"
PROJECT_MANAGER = "project_manager"
DEVELOPER = "developer"
OPERATOR = "operator"
VIEWER = "viewer"
AUDITOR = "auditor"


ROLE_DESCRIPTIONS: Dict[str, str] = {
    PLATFORM_OWNER: "Full platform ownership",
    PLATFORM_ADMIN: "Platform administration",
    ORGANIZATION_OWNER: "Organization ownership",
    ORGANIZATION_ADMIN: "Organization administration",
    PROJECT_MANAGER: "Project planning and delivery",
    DEVELOPER: "Build and deploy applications",
    OPERATOR: "Operate runtime and deployments",
    VIEWER: "Read-only access",
    AUDITOR: "Audit and compliance review",
}


def role_registry() -> Dict[str, str]:
    return dict(ROLE_DESCRIPTIONS)


def available_roles() -> List[str]:
    return sorted(ROLE_DESCRIPTIONS)
