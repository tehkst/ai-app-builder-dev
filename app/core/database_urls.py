from __future__ import annotations

from urllib.parse import urlsplit


POSTGRESQL_SCHEMES = {"postgresql", "postgresql+asyncpg", "postgresql+psycopg2", "postgresql+psycopg"}
SQLITE_SCHEMES = {"sqlite", "sqlite+aiosqlite"}


def database_family(database_url: str) -> str:
    scheme = _scheme(database_url)
    if scheme in POSTGRESQL_SCHEMES:
        return "postgresql"
    if scheme in SQLITE_SCHEMES:
        return "sqlite"
    return "unknown"


def normalize_async_database_url(database_url: str) -> str:
    scheme = _supported_scheme(database_url)
    if scheme == "postgresql":
        return _replace_scheme(database_url, "postgresql+asyncpg")
    if scheme in {"postgresql+psycopg2", "postgresql+psycopg"}:
        return _replace_scheme(database_url, "postgresql+asyncpg")
    if scheme == "sqlite":
        return _replace_scheme(database_url, "sqlite+aiosqlite")
    return database_url


def normalize_sync_database_url(database_url: str) -> str:
    scheme = _supported_scheme(database_url)
    if scheme in {"postgresql", "postgresql+asyncpg", "postgresql+psycopg"}:
        return _replace_scheme(database_url, "postgresql+psycopg2")
    if scheme == "sqlite+aiosqlite":
        return _replace_scheme(database_url, "sqlite")
    return database_url


def _supported_scheme(database_url: str) -> str:
    scheme = _scheme(database_url)
    if scheme not in POSTGRESQL_SCHEMES | SQLITE_SCHEMES:
        raise ValueError(f"Unsupported database URL scheme: {scheme or 'missing'}")
    return scheme


def _scheme(database_url: str) -> str:
    return urlsplit(str(database_url or "").strip()).scheme.lower()


def _replace_scheme(database_url: str, scheme: str) -> str:
    _, separator, remainder = database_url.partition("://")
    if not separator:
        raise ValueError("Database URL must contain a scheme")
    return f"{scheme}://{remainder}"
