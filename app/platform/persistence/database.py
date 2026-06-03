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

if PLATFORM_DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}


platform_engine = create_engine(
    PLATFORM_DATABASE_URL,
    connect_args=connect_args,
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
