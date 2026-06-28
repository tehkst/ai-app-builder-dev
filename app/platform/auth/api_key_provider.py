from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiKeyRecord:
    key_id: str
    owner_user_id: str
    organization_id: str
    tenant_id: str
    active: bool = True


def issue_api_key(key_id: str, owner_user_id: str, organization_id: str, tenant_id: str) -> ApiKeyRecord:
    return ApiKeyRecord(
        key_id=key_id,
        owner_user_id=owner_user_id,
        organization_id=organization_id,
        tenant_id=tenant_id,
    )


def api_key_is_active(record: ApiKeyRecord) -> bool:
    return record.active
