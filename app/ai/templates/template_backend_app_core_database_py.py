from __future__ import annotations


TEMPLATE_PATH = 'backend/app/core/database.py'
TEMPLATE_CONTENT = 'from collections.abc import AsyncGenerator\n\nfrom sqlalchemy.ext.asyncio import (\n    AsyncSession,\n    async_sessionmaker,\n    create_async_engine,\n)\nfrom sqlalchemy.orm import DeclarativeBase\n\nfrom app.core.config import settings\n\n\nclass Base(DeclarativeBase):\n    pass\n\n\nengine = create_async_engine(\n    settings.DATABASE_URL,\n    echo=False,\n)\n\n\nAsyncSessionLocal = async_sessionmaker(\n    engine,\n    expire_on_commit=False,\n)\n\nasync def get_db() -> AsyncGenerator[AsyncSession, None]:\n    async with AsyncSessionLocal() as session:\n        yield session\n\n__all__ = [\n    "Base",\n    "engine",\n    "AsyncSessionLocal",\n    "get_db",\n]\n'
