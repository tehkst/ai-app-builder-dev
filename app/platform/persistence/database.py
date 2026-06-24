import os
from pathlib import Path
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.platform.persistence.models import PlatformBase


BASE_DIR = Path(__file__).resolve().parents[3]
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)


DEFAULT_PLATFORM_DATABASE_URL = "sqlite:///./platform.db"


PLATFORM_DATABASE_URL = os.getenv(
    "PLATFORM_DATABASE_URL",
    DEFAULT_PLATFORM_DATABASE_URL,
)


connect_args = {}
engine_options = {
    "future": True,
    "pool_pre_ping": True,
}

if PLATFORM_DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
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
    PlatformBase.metadata.create_all(bind=platform_engine)


def get_platform_db() -> Generator:
    db = PlatformSessionLocal()

    try:
        yield db
    finally:
        db.close()
