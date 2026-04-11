"""
Async SQLAlchemy engine and session setup for PI Darts Counter.

Design notes:
- A single module-level engine is created once at import time from the URL in
  config.settings.  This is safe because the engine itself is stateless; only
  sessions carry per-request state.
- `get_db()` is an async generator FastAPI dependency.  It yields one
  AsyncSession per request and always closes it in the finally block,
  regardless of whether the handler raised an exception.
- `init_db()` is called once from the startup lifespan event.  It issues
  CREATE TABLE IF NOT EXISTS for every model registered on Base.
"""
import logging

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from typing import AsyncGenerator

from config import settings
from database.models import Base

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
# `check_same_thread=False` is required for SQLite when the same connection
# is used across threads (aiosqlite uses a background thread internally).
# For other databases this connect_arg is silently ignored by the driver.
engine = create_async_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    echo=settings.debug,  # Log SQL statements in debug mode only
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
# expire_on_commit=False prevents SQLAlchemy from expiring ORM objects after
# commit, which would trigger lazy-load queries on already-closed sessions when
# the caller tries to access attributes after await db.commit().
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async database session dependency for FastAPI route handlers.

    Usage:
        async def my_route(db: AsyncSession = Depends(get_db)):
            ...

    The session is committed automatically if the handler returns without
    raising an exception.  Any exception causes a rollback and re-raise so
    the HTTP layer can return the appropriate error response.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Startup initialisation
# ---------------------------------------------------------------------------
async def init_db() -> None:
    """
    Create all database tables on application startup.

    Uses CREATE TABLE IF NOT EXISTS semantics via SQLAlchemy's `create_all`,
    so calling this on a database that already has tables is a safe no-op.
    Any schema migration (column additions, etc.) is out of scope for this
    function and should be handled by a migration tool (e.g. Alembic).
    """
    logger.info("Initialising database at: %s", settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready.")
