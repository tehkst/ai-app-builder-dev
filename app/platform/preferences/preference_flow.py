from __future__ import annotations

from app.platform.preferences.preference_models import PreferenceContext
from app.platform.preferences.preference_store import make_preference, make_profile


def run_demo_preferences() -> PreferenceContext:
    profiles = [
        make_profile("user_platform_owner", "tenant_platform", "Platform Owner", "Asia/Singapore", "en"),
        make_profile("other_user", "other_tenant", "Other User", "UTC", "en"),
    ]
    preferences = [
        make_preference("pref1", "tenant_platform", "user_platform_owner", "default_view", "dashboard"),
        make_preference("pref2", "tenant_platform", "user_platform_owner", "notice_channel", "in_app"),
        make_preference("pref3", "tenant_platform", "user_platform_owner", "theme", "light"),
        make_preference("pref4", "other_tenant", "other_user", "default_view", "tasks"),
    ]
    return PreferenceContext(profiles=profiles, preferences=preferences, metadata={"flow": "preferences"})
