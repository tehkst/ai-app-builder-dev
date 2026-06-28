from __future__ import annotations

from app.platform.adminops.adminops_models import AdminOpsContext
from app.platform.adminops.adminops_store import summarize_adminops
from app.platform.webconsole.console_models import ConsoleCard, ConsoleView


def adminops_view(context: AdminOpsContext, tenant_id: str) -> ConsoleView:
    summary = summarize_adminops(
        context.settings,
        context.api_keys,
        context.integrations,
        context.webhooks,
        context.flags,
        tenant_id,
    )
    return ConsoleView(
        view_id="adminops",
        title="Administration",
        cards=[
            ConsoleCard("settings", "Settings", str(summary.setting_count), "healthy", {}),
            ConsoleCard("keys", "API Keys", str(summary.active_key_count), "healthy", {}),
            ConsoleCard("integrations", "Integrations", str(summary.integration_count), "healthy", {}),
            ConsoleCard("webhooks", "Webhooks", str(summary.active_webhook_count), "healthy", {}),
            ConsoleCard("flags", "Feature Flags", str(summary.enabled_flag_count), "healthy", {}),
        ],
    )
