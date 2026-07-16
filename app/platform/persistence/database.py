import os
from pathlib import Path
from typing import Generator, Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.platform.persistence.models import PlatformBase
from app.platform.persistence.readiness import resolve_platform_database_url


BASE_DIR = Path(__file__).resolve().parents[3]
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)


PLATFORM_DATABASE_URL, PLATFORM_DATABASE_CONFIGURATION_SOURCE = resolve_platform_database_url()
DEFAULT_PLATFORM_DB_CONNECT_TIMEOUT_SECONDS = 5


def platform_db_connect_timeout_seconds(value: Optional[str] = None) -> int:
    raw = value if value is not None else os.getenv("PLATFORM_DB_CONNECT_TIMEOUT_SECONDS")
    try:
        timeout = int(raw) if raw is not None else DEFAULT_PLATFORM_DB_CONNECT_TIMEOUT_SECONDS
    except (TypeError, ValueError):
        return DEFAULT_PLATFORM_DB_CONNECT_TIMEOUT_SECONDS
    return timeout if 1 <= timeout <= 30 else DEFAULT_PLATFORM_DB_CONNECT_TIMEOUT_SECONDS


PLATFORM_DB_CONNECT_TIMEOUT_SECONDS = platform_db_connect_timeout_seconds()


connect_args = {}
engine_options = {
    "future": True,
    "pool_pre_ping": True,
}

if PLATFORM_DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    connect_args = {"connect_timeout": PLATFORM_DB_CONNECT_TIMEOUT_SECONDS}
    engine_options.update(
        {
            "pool_size": int(os.getenv("PLATFORM_DB_POOL_SIZE", "5")),
            "max_overflow": int(os.getenv("PLATFORM_DB_MAX_OVERFLOW", "10")),
            "pool_recycle": int(os.getenv("PLATFORM_DB_POOL_RECYCLE_SECONDS", "1800")),
        }
    )


platform_engine = create_engine(
    PLATFORM_DATABASE_URL,
    connect_args=connect_args,
    **engine_options,
)


PlatformSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=platform_engine,
)


def create_platform_tables() -> None:
    if platform_engine.dialect.name != "postgresql":
        PlatformBase.metadata.create_all(bind=platform_engine)
        return
    with platform_engine.begin() as connection:
        connection.execute(text("SELECT pg_advisory_lock(85787156520)"))
        try:
            PlatformBase.metadata.create_all(bind=connection)
        finally:
            connection.execute(text("SELECT pg_advisory_unlock(85787156520)"))


def verify_platform_persistence_connection(readiness: dict) -> dict:
    result = dict(readiness)
    try:
        with platform_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        commissioned = (
            result.get("mode") == "shared_transactional"
            and result.get("production_safe") is True
            and result.get("cross_instance_coordination") == "supported"
        )
        result.update({"connection_verified": True, "active": True, "commissioned": commissioned})
    except Exception:
        reasons = list(result.get("reasons") or [])
        reasons.append("The configured platform database did not pass a bounded connectivity check.")
        result.update({"connection_verified": False, "active": False, "durable_runtime_available": False, "commissioned": False, "reasons": reasons})
    return result


def get_platform_db() -> Generator:
    db = PlatformSessionLocal()

    try:
        yield db
    finally:
        db.close()
