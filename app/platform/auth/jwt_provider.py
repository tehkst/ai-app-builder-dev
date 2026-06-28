from __future__ import annotations

from typing import Dict


def issue_jwt_claims(user_id: str, organization_id: str, tenant_id: str) -> Dict[str, str]:
    return {
        "sub": user_id,
        "org": organization_id,
        "tenant": tenant_id,
        "typ": "access",
    }


def validate_jwt_claims(claims: Dict[str, str]) -> bool:
    return bool(claims.get("sub") and claims.get("org") and claims.get("tenant"))
