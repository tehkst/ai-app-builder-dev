from __future__ import annotations


async def initialize_identity_tables() -> None:
    import app.models  # noqa: F401 - register customer identity models
    from app.core.database import Base, engine

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
