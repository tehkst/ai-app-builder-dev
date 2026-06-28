from __future__ import annotations

from app.platform.auth.auth_models import AuthenticatedPrincipal
from app.platform.saas_portal.portal_models import PortalCard, PortalView


def settings_view(principal: AuthenticatedPrincipal) -> PortalView:
    cards = [
        PortalCard("profile", "Profile", principal.identity.display_name, "active", {}),
        PortalCard("organization", "Organization", principal.organization_id, "active", {}),
        PortalCard("tenant", "Tenant", principal.tenant_id, "active", {}),
    ]
    return PortalView("settings_view", "Settings", cards)
