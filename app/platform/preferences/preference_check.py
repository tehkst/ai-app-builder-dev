from __future__ import annotations

from app.platform.preferences.preference_flow import run_demo_preferences
from app.platform.preferences.preference_store import (
    find_preference,
    preferences_for_tenant,
    preferences_for_user,
    profiles_for_tenant,
    summarize_preferences,
    update_preference,
)


def main() -> None:
    data = run_demo_preferences()
    assert len(data.profiles) == 2, data
    assert len(data.preferences) == 4, data

    tenant_profiles = profiles_for_tenant(data.profiles, "tenant_platform")
    assert len(tenant_profiles) == 1, tenant_profiles

    tenant_preferences = preferences_for_tenant(data.preferences, "tenant_platform")
    assert len(tenant_preferences) == 3, tenant_preferences

    user_preferences = preferences_for_user(data.preferences, "user_platform_owner")
    assert len(user_preferences) == 3, user_preferences

    theme = find_preference(data.preferences, "user_platform_owner", "theme")
    assert theme is not None, data.preferences
    assert theme.value == "light", theme

    updated = update_preference(theme, "dark")
    assert updated.value == "dark", updated
    assert updated.key == "theme", updated

    summary = summarize_preferences(data.profiles, data.preferences, "tenant_platform", "user_platform_owner")
    assert summary.profile_count == 2, summary
    assert summary.preference_count == 4, summary
    assert summary.tenant_preference_count == 3, summary
    assert summary.user_preference_count == 3, summary

    print("PREFERENCE CHECK PASSED")


if __name__ == "__main__":
    main()
