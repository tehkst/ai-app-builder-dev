from __future__ import annotations

from typing import Any


def independent_review_enabled() -> bool:
    from app.platform.runtime.settings_store import INDEPENDENT_REVIEW_ENABLED_KEY, get_setting

    return get_setting(INDEPENDENT_REVIEW_ENABLED_KEY) != "false"


def independent_review_status() -> dict[str, Any]:
    return {"enabled": independent_review_enabled()}


def save_independent_review_setting(payload: dict[str, Any]) -> dict[str, Any]:
    from app.platform.runtime.settings_store import INDEPENDENT_REVIEW_ENABLED_KEY, set_setting

    enabled = bool(payload.get("enabled", True))
    set_setting(INDEPENDENT_REVIEW_ENABLED_KEY, "true" if enabled else "false")
    return independent_review_status()
