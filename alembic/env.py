"""Alembic environment – supports both sync (offline) and async (online) modes.

Async mode is used for PostgreSQL (asyncpg) in production.
Sync mode is used for SQLite in testing and offline generation.

The DATABASE_URL environment variable overrides alembic.ini's sqlalchemy.url.
"""
from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ── Athena models import (ensures all tables are registered in metadata) ─────
# This import MUST happen before any reference to Base.metadata
import athena.db.models  # noqa: F401
from athena.db.base import Base, metadata as target_metadata

# ── Alembic Config object ─────────────────────────────────────────────────────
config = context.config

# Override sqlalchemy.url from environment variable if provided
_db_url = os.environ.get("DATABASE_URL")
if _db_url:
    config.set_main_option("sqlalchemy.url", _db_url)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Naming convention is already on metadata via Base ────────────────────────
# target_metadata already carries NAMING_CONVENTION from athena.db.base


def include_object(obj, name, type_, reflected, compare_to):  # noqa: ANN001
    """Filter out objects we don't want Alembic to manage."""
    # Example: exclude views or external tables
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine;
    by skipping the Engine creation we don't even need a DBAPI to be available.
    Calls to context.execute() emit the given string to the script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        render_as_batch=True,  # Required for SQLite ALTER TABLE support
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Execute migrations within an existing connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        render_as_batch=True,  # Required for SQLite ALTER TABLE support
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode using an async engine.

    In this scenario we need to create an Engine and associate
    a connection with the context.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Detects whether the URL is async-compatible and dispatches accordingly.
    """
    url = config.get_main_option("sqlalchemy.url", "")

    # Async drivers: asyncpg, aiosqlite
    if "+asyncpg" in url or "+aiosqlite" in url:
        asyncio.run(run_async_migrations())
    else:
        # Synchronous path (plain sqlite://, postgresql://, etc.)
        from sqlalchemy import engine_from_config
        from sqlalchemy import pool as _pool

        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=_pool.NullPool,
        )

        with connectable.connect() as connection:
            do_run_migrations(connection)

        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
