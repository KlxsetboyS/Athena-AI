"""Session helpers – sync (tests/migrations) and async (production)."""
from __future__ import annotations

from collections.abc import AsyncGenerator, Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker


# ── Synchronous (used by Alembic / validation scripts) ───────────────────────

def build_engine(url: str, **kwargs) -> Engine:
    """Create a synchronous SQLAlchemy engine."""
    return create_engine(url, **kwargs)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a synchronous session factory."""
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session(factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    """Yield a managed synchronous session (commit on success, rollback on error)."""
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def ping(engine: Engine) -> bool:
    """Return True if the database is reachable via a synchronous engine."""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True


# ── Asynchronous (production use) ─────────────────────────────────────────────

def build_async_engine(url: str, **kwargs) -> AsyncEngine:
    """Create an async SQLAlchemy engine.

    Args:
        url:     Async-compatible URL, e.g. ``postgresql+asyncpg://...`` or
                 ``sqlite+aiosqlite:///:memory:``.
        **kwargs: Forwarded to :func:`create_async_engine`.
    """
    return create_async_engine(url, **kwargs)


def build_async_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory bound to *engine*."""
    return async_sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


async def get_async_session(
    factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Async context manager that yields a managed :class:`AsyncSession`.

    Commits on success, rolls back on error.  Intended for use with
    FastAPI ``Depends`` or any async DI framework::

        async for session in get_async_session(factory):
            ...
    """
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def async_ping(engine: AsyncEngine) -> bool:
    """Return True if the database is reachable via an async engine."""
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return True
