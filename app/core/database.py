import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")


def normalize_async_database_url(database_url: str) -> str:
    """Return a SQLAlchemy async PostgreSQL URL.

    Railway PostgreSQL commonly provides URLs beginning with
    postgresql://. The app uses SQLAlchemy's async engine, so the
    driver scheme must be postgresql+asyncpg://.
    """

    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return database_url


if not DATABASE_URL:
    raise ValueError("DATABASE_URL is missing in .env")


engine = create_async_engine(
    normalize_async_database_url(DATABASE_URL),
    echo=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
