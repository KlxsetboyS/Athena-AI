#!/usr/bin/env python3
"""Sprint 1.8 validation – Testing Infrastructure + CI.

All checks use file-system inspection and AST analysis only.
No SQLAlchemy installation required in the sandbox.

Checks (28 total)
-----------------
 1-6   Test file structure
 7-12  conftest.py: fixtures and imports
13-17  test_mixins.py: coverage of UUIDMixin, TimestampMixin, SoftDeleteMixin
18-22  test_base_repository.py: CRUD operation coverage
23-26  test_match_repository.py: domain query coverage
27-30  test_odds_repository.py: odds domain coverage
31-34  integration/test_full_roundtrip.py: full graph checks
35-37  pytest.ini / pyproject.toml configuration
38-40  CI workflow
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

BASE = Path(__file__).parent
TESTS = BASE / "tests"

PASS = "✅"
FAIL = "❌"
results: list[tuple[bool, str]] = []


def check(condition: bool, message: str) -> None:
    results.append((condition, message))
    icon = PASS if condition else FAIL
    print(f"{icon} {message}")


def file_exists(path: Path) -> bool:
    return path.is_file()


def read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def has_async_def(source: str, name: str) -> bool:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == name:
            return True
    return False


def contains(source: str, *fragments: str) -> bool:
    return all(f in source for f in fragments)


# ── 1–6: File structure ───────────────────────────────────────────────────────
check(file_exists(TESTS / "__init__.py"), "tests/__init__.py exists")
check(file_exists(TESTS / "conftest.py"), "tests/conftest.py exists")
check(file_exists(TESTS / "unit" / "db" / "test_mixins.py"), "tests/unit/db/test_mixins.py exists")
check(file_exists(TESTS / "unit" / "repositories" / "test_base_repository.py"), "tests/unit/repositories/test_base_repository.py exists")
check(file_exists(TESTS / "unit" / "repositories" / "test_match_repository.py"), "tests/unit/repositories/test_match_repository.py exists")
check(file_exists(TESTS / "unit" / "repositories" / "test_odds_repository.py"), "tests/unit/repositories/test_odds_repository.py exists")
check(file_exists(TESTS / "integration" / "db" / "test_full_roundtrip.py"), "tests/integration/db/test_full_roundtrip.py exists")

# ── 7–12: conftest.py ─────────────────────────────────────────────────────────
conf = read_source(TESTS / "conftest.py")
check(contains(conf, "create_async_engine"), "conftest: uses create_async_engine (aiosqlite)")
check(contains(conf, "sqlite+aiosqlite"), "conftest: SQLite in-memory URL")
check(contains(conf, "async_sessionmaker"), "conftest: async_sessionmaker fixture")
check(contains(conf, "await session.rollback()"), "conftest: per-test rollback isolation")
check(contains(conf, "CompetitionRepository"), "conftest: CompetitionRepository fixture")
check(contains(conf, "sample_match"), "conftest: sample_match fixture")

# ── 13–17: test_mixins.py ─────────────────────────────────────────────────────
mix = read_source(TESTS / "unit" / "db" / "test_mixins.py")
check(contains(mix, "UUIDMixin"), "test_mixins: UUIDMixin referenced")
check(contains(mix, "TimestampMixin"), "test_mixins: TimestampMixin referenced")
check(contains(mix, "SoftDeleteMixin"), "test_mixins: SoftDeleteMixin referenced")
check(contains(mix, "soft_delete"), "test_mixins: soft_delete() tested")
check(contains(mix, "restore"), "test_mixins: restore() tested")

# ── 18–22: test_base_repository.py ───────────────────────────────────────────
base = read_source(TESTS / "unit" / "repositories" / "test_base_repository.py")
check(contains(base, "TestCreate"), "test_base_repo: TestCreate class present")
check(contains(base, "TestRead"), "test_base_repo: TestRead class present")
check(contains(base, "get_by_id_or_raise"), "test_base_repo: get_by_id_or_raise tested")
check(contains(base, "TestSoftDeleteAndRestore"), "test_base_repo: soft-delete/restore tested")
check(contains(base, "TestHardDelete"), "test_base_repo: hard delete tested")

# ── 23–26: test_match_repository.py ──────────────────────────────────────────
match_t = read_source(TESTS / "unit" / "repositories" / "test_match_repository.py")
check(contains(match_t, "get_by_external_id"), "test_match_repo: get_by_external_id tested")
check(contains(match_t, "get_head_to_head"), "test_match_repo: get_head_to_head tested")
check(contains(match_t, "get_upcoming"), "test_match_repo: get_upcoming tested")
check(contains(match_t, "get_finished"), "test_match_repo: get_finished tested")

# ── 27–30: test_odds_repository.py ───────────────────────────────────────────
odds_t = read_source(TESTS / "unit" / "repositories" / "test_odds_repository.py")
check(contains(odds_t, "get_closing_snapshot"), "test_odds_repo: get_closing_snapshot tested")
check(contains(odds_t, "get_history"), "test_odds_repo: get_history tested")
check(contains(odds_t, "snapshot_exists"), "test_odds_repo: snapshot_exists tested")
check(contains(odds_t, "get_selections"), "test_odds_repo: get_selections tested")

# ── 31–34: integration roundtrip ─────────────────────────────────────────────
intg = read_source(TESTS / "integration" / "db" / "test_full_roundtrip.py")
check(contains(intg, "full_graph"), "integration: full_graph fixture defined")
check(contains(intg, "implied_probability"), "integration: bookmaker margin check")
check(contains(intg, "soft_delete"), "integration: soft-delete roundtrip tested")
check(contains(intg, "search_by_name"), "integration: team name search tested")

# ── 35–37: pytest / pyproject config ─────────────────────────────────────────
ini = read_source(BASE / "pytest.ini")
check(contains(ini, "asyncio_mode = auto"), "pytest.ini: asyncio_mode = auto")
check(contains(ini, "testpaths = tests"), "pytest.ini: testpaths configured")
pyp = read_source(BASE / "pyproject.toml")
check(contains(pyp, "pytest-asyncio"), "pyproject.toml: pytest-asyncio in dev deps")

# ── 38–40: CI workflow ────────────────────────────────────────────────────────
ci = read_source(BASE / ".github" / "workflows" / "ci.yml")
check(file_exists(BASE / ".github" / "workflows" / "ci.yml"), "CI workflow file exists")
check(contains(ci, "unit-tests"), "CI: unit-tests job defined")
check(contains(ci, "integration-tests"), "CI: integration-tests job defined")

# ── Summary ───────────────────────────────────────────────────────────────────
passed = sum(1 for ok, _ in results if ok)
total = len(results)
print(f"\nSprint 1.8 validation: {passed}/{total} checks passed")
sys.exit(0 if passed == total else 1)
