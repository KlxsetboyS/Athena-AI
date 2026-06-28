"""Database management CLI commands for Athena AI.

Usage examples:
    python -m athena.cli.db upgrade
    python -m athena.cli.db downgrade
    python -m athena.cli.db current
    python -m athena.cli.db history
    python -m athena.cli.db revision --message "add feature table"
    python -m athena.cli.db verify
    python -m athena.cli.db stamp --revision head

Environment variables:
    DATABASE_URL  – SQLAlchemy connection URL.
                    Defaults to sqlite:///athena.db (local development).
                    For async PostgreSQL: postgresql+asyncpg://user:pass@host/db
                    For async SQLite (tests): sqlite+aiosqlite:///athena.db
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_alembic_config(database_url: str | None = None) -> "alembic.config.Config":  # type: ignore[name-defined]  # noqa: F821
    """Build an Alembic Config pointing at the project's alembic.ini."""
    try:
        from alembic.config import Config
    except ImportError as exc:
        print("ERROR: alembic is not installed. Run: pip install alembic", file=sys.stderr)
        raise SystemExit(1) from exc

    # Locate alembic.ini relative to this file's package root
    ini_path = Path(__file__).resolve().parents[2] / "alembic.ini"
    if not ini_path.exists():
        print(f"ERROR: alembic.ini not found at {ini_path}", file=sys.stderr)
        raise SystemExit(1)

    cfg = Config(str(ini_path))

    # Override database URL: env var > argument > alembic.ini default
    url = database_url or os.environ.get("DATABASE_URL")
    if url:
        cfg.set_main_option("sqlalchemy.url", url)

    return cfg


# ── Commands ─────────────────────────────────────────────────────────────────

def cmd_upgrade(args: argparse.Namespace) -> None:
    """Apply pending migrations up to *revision* (default: head)."""
    from alembic import command

    cfg = _get_alembic_config(args.db_url)
    revision = args.revision or "head"
    print(f"[db upgrade] Applying migrations up to: {revision}")
    command.upgrade(cfg, revision)
    print("[db upgrade] Done.")


def cmd_downgrade(args: argparse.Namespace) -> None:
    """Revert migrations down to *revision* (default: -1, one step back)."""
    from alembic import command

    cfg = _get_alembic_config(args.db_url)
    revision = args.revision or "-1"
    print(f"[db downgrade] Reverting to: {revision}")
    command.downgrade(cfg, revision)
    print("[db downgrade] Done.")


def cmd_current(args: argparse.Namespace) -> None:
    """Show the current migration revision."""
    from alembic import command

    cfg = _get_alembic_config(args.db_url)
    command.current(cfg, verbose=args.verbose)


def cmd_history(args: argparse.Namespace) -> None:
    """Show migration history."""
    from alembic import command

    cfg = _get_alembic_config(args.db_url)
    command.history(cfg, verbose=args.verbose)


def cmd_revision(args: argparse.Namespace) -> None:
    """Generate a new migration revision script."""
    from alembic import command

    cfg = _get_alembic_config(args.db_url)
    command.revision(
        cfg,
        message=args.message,
        autogenerate=args.autogenerate,
    )


def cmd_stamp(args: argparse.Namespace) -> None:
    """Stamp the database at *revision* without running migrations."""
    from alembic import command

    cfg = _get_alembic_config(args.db_url)
    revision = args.revision or "head"
    print(f"[db stamp] Stamping at: {revision}")
    command.stamp(cfg, revision)
    print("[db stamp] Done.")


def cmd_verify(args: argparse.Namespace) -> None:
    """Verify that the database schema matches the current model metadata.

    Connects to the database and compares the live schema against the
    SQLAlchemy metadata.  Exits with code 1 if there are differences.
    """
    try:
        from alembic.runtime.migration import MigrationContext
        from alembic.autogenerate import compare_metadata
        from sqlalchemy import create_engine
    except ImportError as exc:
        print("ERROR: alembic is not installed.", file=sys.stderr)
        raise SystemExit(1) from exc

    # Import models to populate metadata
    import athena.db.models  # noqa: F401
    from athena.db.base import metadata

    cfg = _get_alembic_config(args.db_url)
    url = cfg.get_main_option("sqlalchemy.url", "sqlite:///athena.db")

    # Use sync engine for introspection (strip async prefix for compat)
    sync_url = url.replace("+asyncpg", "").replace("+aiosqlite", "")
    engine = create_engine(sync_url)

    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        diffs = compare_metadata(ctx, metadata)

    if diffs:
        print("[db verify] ❌ Schema drift detected:")
        for diff in diffs:
            print(f"  {diff}")
        raise SystemExit(1)
    else:
        print("[db verify] ✅ Schema matches model metadata — no drift detected.")


# ── CLI entrypoint ────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the db sub-commands."""
    parser = argparse.ArgumentParser(
        prog="python -m athena.cli.db",
        description="Athena AI – database migration management",
    )
    parser.add_argument(
        "--db-url",
        metavar="URL",
        default=None,
        help="SQLAlchemy database URL (overrides DATABASE_URL env var and alembic.ini)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # upgrade
    p_up = sub.add_parser("upgrade", help="Apply pending migrations (default: head)")
    p_up.add_argument("revision", nargs="?", default="head", help="Target revision (default: head)")
    p_up.set_defaults(func=cmd_upgrade)

    # downgrade
    p_down = sub.add_parser("downgrade", help="Revert migrations (default: -1)")
    p_down.add_argument("revision", nargs="?", default="-1", help="Target revision (default: -1)")
    p_down.set_defaults(func=cmd_downgrade)

    # current
    p_cur = sub.add_parser("current", help="Show current revision")
    p_cur.add_argument("-v", "--verbose", action="store_true")
    p_cur.set_defaults(func=cmd_current)

    # history
    p_hist = sub.add_parser("history", help="Show migration history")
    p_hist.add_argument("-v", "--verbose", action="store_true")
    p_hist.set_defaults(func=cmd_history)

    # revision
    p_rev = sub.add_parser("revision", help="Generate a new migration script")
    p_rev.add_argument("-m", "--message", required=True, help="Migration description")
    p_rev.add_argument(
        "--autogenerate", action="store_true",
        help="Autogenerate migration by comparing models to DB",
    )
    p_rev.set_defaults(func=cmd_revision)

    # stamp
    p_stamp = sub.add_parser("stamp", help="Stamp DB at revision without running migrations")
    p_stamp.add_argument("revision", nargs="?", default="head")
    p_stamp.set_defaults(func=cmd_stamp)

    # verify
    p_ver = sub.add_parser("verify", help="Verify schema matches metadata (no drift)")
    p_ver.set_defaults(func=cmd_verify)

    return parser


def main() -> None:
    """CLI entrypoint."""
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
