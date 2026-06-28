from __future__ import annotations

from typing import Iterable, List, Optional

from app.platform.preferences.preference_models import PreferenceProfile, PreferenceSummary, UserPreference


def make_profile(user_id: str, tenant_id: str, display_name: str, timezone: str, language: str) -> PreferenceProfile:
    return PreferenceProfile(user_id, tenant_id, display_name, timezone, language)


def make_preference(preference_id: str, tenant_id: str, user_id: str, key: str, value: str) -> UserPreference:
    return UserPreference(preference_id, tenant_id, user_id, key, value)


def profiles_for_tenant(profiles: Iterable[PreferenceProfile], tenant_id: str) -> List[PreferenceProfile]:
    return [profile for profile in profiles if profile.tenant_id == tenant_id]


def preferences_for_tenant(preferences: Iterable[UserPreference], tenant_id: str) -> List[UserPreference]:
    return [preference for preference in preferences if preference.tenant_id == tenant_id]


def preferences_for_user(preferences: Iterable[UserPreference], user_id: str) -> List[UserPreference]:
    return [preference for preference in preferences if preference.user_id == user_id]


def find_preference(preferences: Iterable[UserPreference], user_id: str, key: str) -> Optional[UserPreference]:
    for preference in preferences:
        if preference.user_id == user_id and preference.key == key:
            return preference
    return None


def update_preference(preference: UserPreference, value: str) -> UserPreference:
    return UserPreference(
        preference.preference_id,
        preference.tenant_id,
        preference.user_id,
        preference.key,
        value,
    )


def summarize_preferences(
    profiles: Iterable[PreferenceProfile],
    preferences: Iterable[UserPreference],
    tenant_id: str,
    user_id: str,
) -> PreferenceSummary:
    profile_list = list(profiles)
    preference_list = list(preferences)
    return PreferenceSummary(
        profile_count=len(profile_list),
        preference_count=len(preference_list),
        tenant_preference_count=len(preferences_for_tenant(preference_list, tenant_id)),
        user_preference_count=len(preferences_for_user(preference_list, user_id)),
    )
