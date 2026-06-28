from __future__ import annotations

from app.platform.adminops.adminops_models import AdminOpsContext
from app.platform.adminops.adminops_store import summarize_adminops
from app.platform.saas_portal.portal_models import PortalCard, PortalView


def portal_adminops_view(context: AdminOpsContext, tenant_id: str) -> PortalView:
    summary = summarize_adminops(
        context.settings,
        context.api_keys,
        context.integrations,
        context.webhooks,
        context.flags,
        tenant_id,
    )
    return PortalView(
        view_id="portal_adminops",
        title="Administration",
        cards=[
            PortalCard("settings", "Settings", str(summary.setting_count), "healthy", {}),
            PortalCard("keys", "API Keys", str(summary.active_key_count), "healthy", {}),
            PortalCard("integrations", "Integrations", str(summary.integration_count), "healthy", {}),
            PortalCard("flags", "Feature Flags", str(summary.enabled_flag_count), "healthy", {}),
        ],
    )
