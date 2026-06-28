"""Database bootstrap utility for Athena AI.

Convenience script for common operations during development and CI.

Usage:
    python db_bootstrap.py upgrade          # Apply all migrations
    python db_bootstrap.py downgrade        # Revert last migration
    python db_bootstrap.py reset            # Drop all + upgrade head (DESTRUCTIVE)
    python db_bootstrap.py verify           # Check schema drift
    python db_bootstrap.py current          # Show current revision

    DATABASE_URL=postgresql+asyncpg://user:pass@localhost/athena python db_bootstrap.py upgrade

Environment variables:
    DATABASE_URL  – overrides the default sqlite:///athena.db
"""
from __future__ import annotations

import sys

from athena.cli.db import main


def reset_database(db_url: str | None = None) -> None:
    """Drop all tables and re-apply migrations from scratch.

    ⚠️  DESTRUCTIVE — only for development / CI.
    """
    import os
    from sqlalchemy import create_engine

    url = db_url or os.environ.get("DATABASE_URL", "sqlite:///athena.db")
    # Strip async driver prefix for synchronous introspection
    sync_url = url.replace("+asyncpg", "").replace("+aiosqlite", "")

    # Import models to ensure metadata is fully populated
    import athena.db.models  # noqa: F401
    from athena.db.base import Base

    engine = create_engine(sync_url)
    print("[reset] Dropping all tables...")
    Base.metadata.drop_all(engine)
    engine.dispose()
    print("[reset] Done. Running upgrade head...")

    # Now run alembic upgrade head
    sys.argv = ["db_bootstrap.py", "upgrade", "head"]
    if db_url:
        sys.argv = ["db_bootstrap.py", "--db-url", db_url, "upgrade", "head"]
    main()


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "reset":
        db_url = None
        # Look for --db-url flag
        for i, arg in enumerate(sys.argv):
            if arg == "--db-url" and i + 1 < len(sys.argv):
                db_url = sys.argv[i + 1]
        reset_database(db_url)
    else:
        main()
