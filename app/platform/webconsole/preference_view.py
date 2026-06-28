from __future__ import annotations

from app.platform.preferences.preference_models import PreferenceContext
from app.platform.preferences.preference_store import summarize_preferences
from app.platform.webconsole.console_models import ConsoleCard, ConsoleView


def admin_preference_view(context: PreferenceContext, tenant_id: str, user_id: str) -> ConsoleView:
    summary = summarize_preferences(context.profiles, context.preferences, tenant_id, user_id)
    return ConsoleView(
        view_id="admin_preferences",
        title="Preferences",
        cards=[
            ConsoleCard("profiles", "Profiles", str(summary.profile_count), "healthy", {}),
            ConsoleCard("preferences", "Preferences", str(summary.preference_count), "healthy", {}),
            ConsoleCard("tenant", "Tenant Preferences", str(summary.tenant_preference_count), "healthy", {}),
            ConsoleCard("user", "User Preferences", str(summary.user_preference_count), "healthy", {}),
        ],
    )
