from __future__ import annotations

from app.platform.preferences.preference_models import PreferenceContext
from app.platform.preferences.preference_store import summarize_preferences
from app.platform.saas_portal.portal_models import PortalCard, PortalView


def portal_preference_view(context: PreferenceContext, tenant_id: str, user_id: str) -> PortalView:
    summary = summarize_preferences(context.profiles, context.preferences, tenant_id, user_id)
    return PortalView(
        view_id="portal_preferences",
        title="Preferences",
        cards=[
            PortalCard("tenant", "Tenant Preferences", str(summary.tenant_preference_count), "healthy", {}),
            PortalCard("user", "My Preferences", str(summary.user_preference_count), "healthy", {}),
        ],
    )
