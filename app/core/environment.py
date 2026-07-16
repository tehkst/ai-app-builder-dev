from __future__ import annotations

from typing import Mapping


KNOWN_PRODUCTION_CLOUD_RUN_SERVICES = frozenset({"ai-software-factory-production"})
PRODUCTION_MARKERS = frozenset({"prod", "production"})
STAGING_MARKERS = frozenset({"stage", "staging"})


def classify_environment(values: Mapping[str, str]) -> str:
    """Classify runtime identity without treating every Cloud Run service as production."""
    explicit = str(values.get("ENVIRONMENT") or values.get("APP_ENV") or "").strip().lower()
    if explicit in PRODUCTION_MARKERS:
        return "production"
    if explicit in STAGING_MARKERS:
        return "staging"

    service = str(values.get("K_SERVICE") or "").strip().lower()
    if service in KNOWN_PRODUCTION_CLOUD_RUN_SERVICES:
        return "production"
    if service and "staging" in service:
        return "staging"
    return "development"


def is_production_environment(values: Mapping[str, str]) -> bool:
    return classify_environment(values) == "production"
