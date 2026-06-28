"""Unit tests for OddsRepository and BookmakerRepository.

Coverage targets
----------------
BookmakerRepository
  - get_by_slug()
  - get_active()

OddsRepository
  - get_latest_snapshot()
  - get_closing_snapshot()
  - get_history()           (chronological ordering, from_time filter)
  - get_by_bookmaker()
  - get_by_external_ref()   (deduplication key)
  - snapshot_exists()
  - get_selections()
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest_asyncio

from athena.db.enums import OddsFormat, OddsMarket, SelectionType
from athena.db.models.odds_selection import OddsSelection
from athena.db.models.odds_snapshot import OddsSnapshot
from athena.repositories.odds import BookmakerRepository


# ── Helpers ───────────────────────────────────────────────────────────────────

BASE_TIME = datetime(2024, 1, 14, 10, 0, tzinfo=timezone.utc)


@pytest_asyncio.fixture(scope="function", loop_scope="function")
async def bookmaker_repo(db_session):
    return BookmakerRepository(db_session)


@pytest_asyncio.fixture(scope="function", loop_scope="function")
async def sample_bookmaker(bookmaker_repo):
    return await bookmaker_repo.create(
        name="Bet365",
        slug="bet365",
        is_exchange=False,
        is_active=True,
    )


@pytest_asyncio.fixture(scope="function", loop_scope="function")
async def sample_bookmaker_2(bookmaker_repo):
    return await bookmaker_repo.create(
        name="Pinnacle",
        slug="pinnacle",
        is_exchange=False,
        is_active=True,
    )


async def _make_snapshot(
    session,
    match_id,
    bookmaker_id,
    *,
    captured_at: datetime = BASE_TIME,
    is_closing: bool = False,
    external_ref: str | None = None,
    market: OddsMarket = OddsMarket.MATCH_WINNER,
) -> OddsSnapshot:
    snap = OddsSnapshot(
        match_id=match_id,
        bookmaker_id=bookmaker_id,
        market=market,
        odds_format=OddsFormat.DECIMAL,
        captured_at=captured_at,
        is_closing=is_closing,
        source="test_source",
        external_ref=external_ref,
    )
    session.add(snap)
    await session.flush()
    return snap


async def _make_selections(session, snapshot_id) -> list[OddsSelection]:
    selections = []
    for sel_type, odd in [
        (SelectionType.HOME, Decimal("2.10")),
        (SelectionType.DRAW, Decimal("3.40")),
        (SelectionType.AWAY, Decimal("3.20")),
    ]:
        sel = OddsSelection(
            snapshot_id=snapshot_id,
            selection_type=sel_type,
            decimal_odd=odd,
        )
        session.add(sel)
        selections.append(sel)
    await session.flush()
    return selections


# ── BookmakerRepository ───────────────────────────────────────────────────────

class TestBookmakerRepository:
    async def test_get_by_slug_found(self, bookmaker_repo, sample_bookmaker):
        result = await bookmaker_repo.get_by_slug("bet365")
        assert result is not None
        assert result.slug == "bet365"

    async def test_get_by_slug_not_found(self, bookmaker_repo):
        result = await bookmaker_repo.get_by_slug("nonexistent-bookie")
        assert result is None

    async def test_get_active_returns_active(
        self, bookmaker_repo, sample_bookmaker, sample_bookmaker_2,
    ):
        active = await bookmaker_repo.get_active()
        slugs = [b.slug for b in active]
        assert "bet365" in slugs
        assert "pinnacle" in slugs

    async def test_get_active_excludes_inactive(self, bookmaker_repo):
        inactive = await bookmaker_repo.create(
            name="Inactive Bookie",
            slug="inactive-bookie",
            is_active=False,
        )
        active = await bookmaker_repo.get_active()
        assert all(b.id != inactive.id for b in active)


# ── OddsRepository ────────────────────────────────────────────────────────────

class TestGetLatestSnapshot:
    async def test_returns_most_recent(
        self, odds_repo, db_session, sample_match, sample_bookmaker,
    ):
        t1 = BASE_TIME
        t2 = BASE_TIME + timedelta(hours=1)
        await _make_snapshot(db_session, sample_match.id, sample_bookmaker.id, captured_at=t1)
        snap2 = await _make_snapshot(db_session, sample_match.id, sample_bookmaker.id, captured_at=t2)
        result = await odds_repo.get_latest_snapshot(sample_match.id, sample_bookmaker.id)
        assert result is not None
        assert result.id == snap2.id

    async def test_returns_none_when_no_snapshots(
        self, odds_repo, sample_match, sample_bookmaker,
    ):
        from uuid import uuid4
        result = await odds_repo.get_latest_snapshot(uuid4(), sample_bookmaker.id)
        assert result is None


class TestGetClosingSnapshot:
    async def test_returns_closing_line(
        self, odds_repo, db_session, sample_match, sample_bookmaker,
    ):
        await _make_snapshot(
            db_session, sample_match.id, sample_bookmaker.id,
            captured_at=BASE_TIME, is_closing=False,
        )
        closing = await _make_snapshot(
            db_session, sample_match.id, sample_bookmaker.id,
            captured_at=BASE_TIME + timedelta(hours=5), is_closing=True,
        )
        result = await odds_repo.get_closing_snapshot(sample_match.id, sample_bookmaker.id)
        assert result is not None
        assert result.id == closing.id
        assert result.is_closing is True

    async def test_returns_none_without_closing_line(
        self, odds_repo, db_session, sample_match, sample_bookmaker,
    ):
        await _make_snapshot(
            db_session, sample_match.id, sample_bookmaker.id,
            captured_at=BASE_TIME, is_closing=False,
        )
        from uuid import uuid4
        result = await odds_repo.get_closing_snapshot(uuid4(), sample_bookmaker.id)
        assert result is None


class TestGetHistory:
    async def test_history_ordered_chronologically(
        self, odds_repo, db_session, sample_match, sample_bookmaker,
    ):
        t_times = [BASE_TIME + timedelta(hours=i) for i in range(4)]
        for t in t_times:
            await _make_snapshot(db_session, sample_match.id, sample_bookmaker.id, captured_at=t)
        history = await odds_repo.get_history(sample_match.id, bookmaker_id=sample_bookmaker.id)
        # SQLite returns naive datetimes; strip tzinfo before membership test
        t_times_naive = [t.replace(tzinfo=None) for t in t_times]
        relevant = [s for s in history if s.captured_at.replace(tzinfo=None) in t_times_naive]
        assert len(relevant) == 4
        captured_times = [s.captured_at for s in relevant]
        assert captured_times == sorted(captured_times)

    async def test_from_time_filter(
        self, odds_repo, db_session, sample_match, sample_bookmaker_2,
    ):
        t_old = BASE_TIME - timedelta(hours=10)
        t_new = BASE_TIME + timedelta(hours=10)
        await _make_snapshot(db_session, sample_match.id, sample_bookmaker_2.id, captured_at=t_old)
        await _make_snapshot(db_session, sample_match.id, sample_bookmaker_2.id, captured_at=t_new)
        cutoff = BASE_TIME
        history = await odds_repo.get_history(
            sample_match.id,
            bookmaker_id=sample_bookmaker_2.id,
            from_time=cutoff,
        )
        # SQLite returns naive datetimes; compare without tzinfo
        cutoff_naive = cutoff.replace(tzinfo=None)
        assert all(s.captured_at.replace(tzinfo=None) >= cutoff_naive for s in history)


class TestExternalRefDeduplication:
    async def test_get_by_external_ref_found(
        self, odds_repo, db_session, sample_match, sample_bookmaker,
    ):
        snap = await _make_snapshot(
            db_session, sample_match.id, sample_bookmaker.id,
            external_ref="unique-ref-001",
        )
        result = await odds_repo.get_by_external_ref("unique-ref-001")
        assert result is not None
        assert result.id == snap.id

    async def test_snapshot_exists_true(
        self, odds_repo, db_session, sample_match, sample_bookmaker,
    ):
        await _make_snapshot(
            db_session, sample_match.id, sample_bookmaker.id,
            external_ref="exists-ref-002",
            captured_at=BASE_TIME + timedelta(minutes=30),
        )
        assert await odds_repo.snapshot_exists("exists-ref-002") is True

    async def test_snapshot_exists_false(self, odds_repo):
        assert await odds_repo.snapshot_exists("phantom-ref-xyz") is False


class TestGetSelections:
    async def test_selections_returned(
        self, odds_repo, db_session, sample_match, sample_bookmaker,
    ):
        snap = await _make_snapshot(
            db_session, sample_match.id, sample_bookmaker.id,
            captured_at=BASE_TIME + timedelta(hours=2),
        )
        await _make_selections(db_session, snap.id)
        selections = await odds_repo.get_selections(snap.id)
        assert len(selections) == 3
        types = {s.selection_type for s in selections}
        assert SelectionType.HOME in types
        assert SelectionType.DRAW in types
        assert SelectionType.AWAY in types

    async def test_selections_decimal_odds_correct(
        self, odds_repo, db_session, sample_match, sample_bookmaker,
    ):
        snap = await _make_snapshot(
            db_session, sample_match.id, sample_bookmaker.id,
            captured_at=BASE_TIME + timedelta(hours=3),
        )
        await _make_selections(db_session, snap.id)
        selections = await odds_repo.get_selections(snap.id)
        odds_map = {s.selection_type: s.decimal_odd for s in selections}
        assert odds_map[SelectionType.HOME] == Decimal("2.10")
        assert odds_map[SelectionType.DRAW] == Decimal("3.40")
        assert odds_map[SelectionType.AWAY] == Decimal("3.20")
