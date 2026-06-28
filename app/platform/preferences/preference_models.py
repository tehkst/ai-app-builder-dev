from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class UserPreference:
    preference_id: str
    tenant_id: str
    user_id: str
    key: str
    value: str


@dataclass(frozen=True)
class PreferenceProfile:
    user_id: str
    tenant_id: str
    display_name: str
    timezone: str
    language: str


@dataclass(frozen=True)
class PreferenceSummary:
    profile_count: int
    preference_count: int
    tenant_preference_count: int
    user_preference_count: int


@dataclass(frozen=True)
class PreferenceContext:
    profiles: List[PreferenceProfile]
    preferences: List[UserPreference]
    metadata: Dict[str, object]
