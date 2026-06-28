from __future__ import annotations

from typing import List

from app.platform.auth.api_key_provider import ApiKeyRecord
from app.platform.saas_portal.portal_models import PortalCard, PortalView


def api_key_view(api_keys: List[ApiKeyRecord]) -> PortalView:
    active = len([key for key in api_keys if key.active])
    cards = [
        PortalCard("api_key_count", "API Keys", str(len(api_keys)), "active", {}),
        PortalCard("active_api_keys", "Active API Keys", str(active), "healthy", {}),
    ]
    return PortalView("api_key_view", "API Keys", cards)


def api_keys_for_tenant(api_keys: List[ApiKeyRecord], tenant_id: str) -> List[ApiKeyRecord]:
    return [key for key in api_keys if key.tenant_id == tenant_id]
