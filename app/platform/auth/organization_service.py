from __future__ import annotations

from typing import Dict

from app.platform.auth.tenant_models import Organization


def create_organization(organization_id: str, name: str) -> Organization:
    return Organization(organization_id=organization_id, name=name)


def organization_registry() -> Dict[str, Organization]:
    org = create_organization("org_platform", "Platform Organization")
    return {org.organization_id: org}


def find_organization(organization_id: str) -> Organization:
    return organization_registry()[organization_id]
