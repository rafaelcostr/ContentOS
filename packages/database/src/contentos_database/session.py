from collections.abc import AsyncGenerator

from contentos_database.models import Base
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_engine = None
_session_factory = None


def init_db(database_url: str, echo: bool = False) -> None:
    global _engine, _session_factory
    _engine = create_async_engine(database_url, echo=echo, pool_pre_ping=True)
    _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def create_tables() -> None:
    if _engine is None:
        raise RuntimeError("Database not initialized.")
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_session_factory():
    """Return async session factory — for V4 intelligence services."""
    return _session_factory
