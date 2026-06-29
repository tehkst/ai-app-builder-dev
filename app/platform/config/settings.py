from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class AppSettings:
    app_env: str
    app_name: str
    port: int
    log_level: str
    database_url: str
    redis_url: str
    secret_key: str


REQUIRED_PRODUCTION_KEYS = [
    "APP_ENV",
    "APP_NAME",
    "PORT",
    "LOG_LEVEL",
    "DATABASE_URL",
    "REDIS_URL",
    "SECRET_KEY",
]

PLACEHOLDER_VALUES = {"", "change-me", "changeme", "replace-me", "secret"}


def read_env(keys: Iterable[str]) -> Dict[str, str]:
    return {key: os.getenv(key, "") for key in keys}


def missing_keys(values: Dict[str, str]) -> List[str]:
    return [key for key, value in values.items() if not value]


def placeholder_keys(values: Dict[str, str]) -> List[str]:
    return [key for key, value in values.items() if value.strip().lower() in PLACEHOLDER_VALUES]


def validate_production_env(values: Dict[str, str]) -> None:
    missing = missing_keys(values)
    placeholders = placeholder_keys(values)
    if missing or placeholders:
        raise ValueError("Invalid production environment: missing={} placeholders={}".format(missing, placeholders))


def load_settings(validate: bool = False) -> AppSettings:
    values = read_env(REQUIRED_PRODUCTION_KEYS)
    if validate:
        validate_production_env(values)
    return AppSettings(
        app_env=values.get("APP_ENV") or "development",
        app_name=values.get("APP_NAME") or "AI Software Factory",
        port=int(values.get("PORT") or "8000"),
        log_level=values.get("LOG_LEVEL") or "info",
        database_url=values.get("DATABASE_URL") or "sqlite+aiosqlite:///./dev.db",
        redis_url=values.get("REDIS_URL") or "redis://localhost:6379/0",
        secret_key=values.get("SECRET_KEY") or "development-secret",
    )
