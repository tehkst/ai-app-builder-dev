from __future__ import annotations

import os


TRUTHY_VALUES = {"1", "true", "yes", "on"}
PRODUCTION_VALUES = {"prod", "production"}


def internal_token_fallback_allowed() -> bool:
    explicit = os.getenv("PLATFORM_ALLOW_INTERNAL_TOKEN_FALLBACK", "").strip().lower()
    if explicit:
        return explicit in TRUTHY_VALUES
    environment = (
        os.getenv("RAILWAY_ENVIRONMENT_NAME")
        or os.getenv("PLATFORM_ENV")
        or os.getenv("ENVIRONMENT")
        or ""
    ).strip().lower()
    return environment not in PRODUCTION_VALUES
