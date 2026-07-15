import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.database_urls import normalize_async_database_url
from app.core.environment import is_production_environment


BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///./app.db"
DATABASE_URL = os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL
if is_production_environment(os.environ) and not os.getenv("DATABASE_URL"):
    raise RuntimeError("Production application persistence requires DATABASE_URL")


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
