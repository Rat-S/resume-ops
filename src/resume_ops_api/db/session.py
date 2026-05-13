from __future__ import annotations

from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from resume_ops_api.db.models import Base


class Database:
    def __init__(self, url: str) -> None:
        self.engine: AsyncEngine = create_async_engine(url, future=True)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

    @asynccontextmanager
    async def session(self) -> AsyncSession:
        async with self.session_factory() as session:
            yield session

    async def bootstrap(self) -> None:
        async with self.engine.begin() as connection:
            await connection.execute(text("PRAGMA journal_mode=WAL;"))
            await connection.run_sync(Base.metadata.create_all)

    async def ping(self) -> None:
        async with self.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def dispose(self) -> None:
        await self.engine.dispose()

