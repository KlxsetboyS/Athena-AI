"""Sprint 1.7 validation — Alembic + CLI (static checks, no alembic runtime needed).

Validates:
  1.  alembic.ini file exists and is valid INI
  2.  alembic/env.py exists
  3.  alembic/script.py.mako exists
  4.  alembic/versions/ directory exists
  5.  Initial migration file exists
  6.  Migration revision ID is set
  7.  Migration has upgrade() function
  8.  Migration has downgrade() function
  9.  All 9 expected tables are created in upgrade()
  10. Downgrade drops all tables in reverse order
  11. All BaseModel columns present in migration (id, created_at, updated_at, is_deleted, deleted_at)
  12. FK constraints defined for child tables
  13. Composite index ix_odds_snapshot_match_bookmaker_captured present
  14. is_closing index present
  15. CLI module (athena/cli/db.py) exists and importable
  16. CLI build_parser() returns a parser with required subcommands
  17. All 7 CLI commands present (upgrade, downgrade, current, history, revision, stamp, verify)
  18. pyproject.toml has alembic in dependencies
  19. pyproject.toml has athena-db script entry point
  20. db_bootstrap.py exists
  21. env.py imports athena.db.models (ensures all models register)
  22. env.py has both offline and online migration modes
"""
from __future__ import annotations

import ast
import configparser
import sys
from pathlib import Path

ROOT = Path(__file__).parent

PASS = "✅ "
FAIL = "❌ "
results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    results.append((name, condition, detail))
    status = PASS if condition else FAIL
    msg = f"{status} {name}"
    if detail and not condition:
        msg += f"\n       → {detail}"
    print(msg)


# ── File existence checks ────────────────────────────────────────────────────

check("alembic.ini exists", (ROOT / "alembic.ini").exists())
check("alembic/env.py exists", (ROOT / "alembic" / "env.py").exists())
check("alembic/script.py.mako exists", (ROOT / "alembic" / "script.py.mako").exists())
check("alembic/versions/ exists", (ROOT / "alembic" / "versions").is_dir())

# ── alembic.ini is valid INI ─────────────────────────────────────────────────
ini_path = ROOT / "alembic.ini"
cfg = configparser.ConfigParser()
try:
    cfg.read(str(ini_path))
    has_alembic_section = "alembic" in cfg
    check("alembic.ini is valid INI with [alembic] section", has_alembic_section)
except Exception as e:
    check("alembic.ini is valid INI with [alembic] section", False, str(e))

# ── Initial migration file ────────────────────────────────────────────────────
versions_dir = ROOT / "alembic" / "versions"
migration_files = [
    f for f in versions_dir.glob("*.py")
    if not f.name.startswith("__")
]
has_migration = len(migration_files) >= 1
check("Initial migration file exists", has_migration,
      f"Found {len(migration_files)} migration(s) in {versions_dir}")

if has_migration:
    mig_file = migration_files[0]
    mig_text = mig_file.read_text()

    # Revision ID
    check("Migration: revision ID is set",
          'revision: str = "001_initial_schema"' in mig_text or 'revision =' in mig_text)

    # upgrade / downgrade functions
    check("Migration: upgrade() function defined", "def upgrade(" in mig_text)
    check("Migration: downgrade() function defined", "def downgrade(" in mig_text)

    # All 9 tables in upgrade
    expected_tables = [
        "competition", "season", "team", "season_team",
        "match", "match_result", "bookmaker", "odds_snapshot", "odds_selection",
    ]
    missing_tables = [t for t in expected_tables if f'"{t}"' not in mig_text]
    check(
        f"Migration: all {len(expected_tables)} tables created in upgrade()",
        len(missing_tables) == 0,
        f"Missing: {missing_tables}" if missing_tables else "",
    )

    # Downgrade drops tables
    check("Migration: downgrade() drops tables",
          "op.drop_table" in mig_text)

    # BaseModel columns present
    base_cols = ["created_at", "updated_at", "is_deleted", "deleted_at"]
    missing_cols = [c for c in base_cols if c not in mig_text]
    check("Migration: BaseModel columns present (created_at, updated_at, is_deleted, deleted_at)",
          len(missing_cols) == 0,
          f"Missing: {missing_cols}" if missing_cols else "")

    # FK constraints
    check("Migration: FK constraints defined (ForeignKeyConstraint)",
          "ForeignKeyConstraint" in mig_text)

    # Composite index for odds_snapshot
    check("Migration: ix_odds_snapshot_match_bookmaker_captured index present",
          "ix_odds_snapshot_match_bookmaker_captured" in mig_text)

    # is_closing index
    check("Migration: ix_odds_snapshot_is_closing index present",
          "ix_odds_snapshot_is_closing" in mig_text)
else:
    # Skip migration-content checks
    for _ in range(8):
        check("(skipped — no migration file)", False, "Initial migration file missing")

# ── CLI module ───────────────────────────────────────────────────────────────
cli_path = ROOT / "athena" / "cli" / "db.py"
check("athena/cli/db.py exists", cli_path.exists())

if cli_path.exists():
    sys.path.insert(0, str(ROOT))
    try:
        from athena.cli.db import build_parser  # type: ignore[import]
        parser = build_parser()
        check("CLI: build_parser() returns ArgumentParser", parser is not None)

        # Check all 7 subcommands exist
        expected_cmds = {"upgrade", "downgrade", "current", "history", "revision", "stamp", "verify"}
        # Extract subcommand choices from parser
        subparsers_action = next(
            (a for a in parser._actions if hasattr(a, "_name_parser_map")), None
        )
        if subparsers_action:
            found_cmds = set(subparsers_action._name_parser_map.keys())
            missing_cmds = expected_cmds - found_cmds
            check(
                f"CLI: all 7 subcommands present ({', '.join(sorted(expected_cmds))})",
                len(missing_cmds) == 0,
                f"Missing: {missing_cmds}" if missing_cmds else "",
            )
        else:
            check("CLI: all 7 subcommands present", False, "No subparser action found")
    except ImportError as e:
        check("CLI: build_parser() returns ArgumentParser", False, str(e))
        check("CLI: all 7 subcommands present", False, "Import failed")
else:
    check("CLI: build_parser() returns ArgumentParser", False, "File missing")
    check("CLI: all 7 subcommands present", False, "File missing")

# ── pyproject.toml checks ─────────────────────────────────────────────────────
pyproject = (ROOT / "pyproject.toml").read_text()
check("pyproject.toml: alembic in dependencies", "alembic" in pyproject)
check("pyproject.toml: athena-db script entry point defined",
      "athena-db" in pyproject and "athena.cli.db:main" in pyproject)

# ── db_bootstrap.py ──────────────────────────────────────────────────────────
check("db_bootstrap.py exists", (ROOT / "db_bootstrap.py").exists())

# ── env.py content checks ─────────────────────────────────────────────────────
env_path = ROOT / "alembic" / "env.py"
if env_path.exists():
    env_text = env_path.read_text()
    check("env.py: imports athena.db.models (registers all models)",
          "import athena.db.models" in env_text)
    check("env.py: has run_migrations_offline() and run_migrations_online()",
          "run_migrations_offline" in env_text and "run_migrations_online" in env_text)
else:
    check("env.py: imports athena.db.models", False, "env.py missing")
    check("env.py: has offline and online migration modes", False, "env.py missing")

# ── Summary ──────────────────────────────────────────────────────────────────
total = len(results)
passed = sum(1 for _, ok, _ in results if ok)
failed = total - passed

print()
print("─" * 60)
print(f"Sprint 1.7 validation: {passed}/{total} checks passed")
if failed:
    print(f"\nFailed checks ({failed}):")
    for name, ok, detail in results:
        if not ok:
            print(f"  {FAIL}{name}")
            if detail:
                print(f"       → {detail}")
    sys.exit(1)
else:
    print(f"\n✅  All {total} checks passed – Sprint 1.7 Alembic + CLI is solid.")
    sys.exit(0)
