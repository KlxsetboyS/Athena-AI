"""Unit tests for OddsService."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from athena.db.enums import OddsMarket
from athena.services.odds_service import OddsService


def _make_service() -> tuple[OddsService, AsyncMock, AsyncMock]:
    odds_repo = AsyncMock()
    book_repo = AsyncMock()
    return OddsService(odds_repo, book_repo), odds_repo, book_repo


def _fake_snapshot() -> MagicMock:
    s = MagicMock()
    s.id = uuid.uuid4()
    return s


def _fake_bookmaker(name: str = "Bet365") -> MagicMock:
    b = MagicMock()
    b.id = uuid.uuid4()
    b.name = name
    return b


class TestGetLatestSnapshot:
    async def test_delegates_to_odds_repo(self):
        svc, odds_repo, _ = _make_service()
        snap = _fake_snapshot()
        match_id = uuid.uuid4()
        book_id = uuid.uuid4()
        odds_repo.get_latest_snapshot.return_value = snap

        result = await svc.get_latest_snapshot(match_id, book_id)

        odds_repo.get_latest_snapshot.assert_awaited_once_with(
            match_id, book_id, OddsMarket.MATCH_WINNER
        )
        assert result is snap

    async def test_custom_market_forwarded(self):
        svc, odds_repo, _ = _make_service()
        match_id, book_id = uuid.uuid4(), uuid.uuid4()
        odds_repo.get_latest_snapshot.return_value = None

        await svc.get_latest_snapshot(match_id, book_id, OddsMarket.BTTS)

        odds_repo.get_latest_snapshot.assert_awaited_once_with(
            match_id, book_id, OddsMarket.BTTS
        )

    async def test_returns_none_when_no_snapshot(self):
        svc, odds_repo, _ = _make_service()
        odds_repo.get_latest_snapshot.return_value = None

        result = await svc.get_latest_snapshot(uuid.uuid4(), uuid.uuid4())

        assert result is None


class TestGetClosingSnapshot:
    async def test_delegates_to_odds_repo(self):
        svc, odds_repo, _ = _make_service()
        snap = _fake_snapshot()
        match_id, book_id = uuid.uuid4(), uuid.uuid4()
        odds_repo.get_closing_snapshot.return_value = snap

        result = await svc.get_closing_snapshot(match_id, book_id)

        odds_repo.get_closing_snapshot.assert_awaited_once_with(
            match_id, book_id, OddsMarket.MATCH_WINNER
        )
        assert result is snap

    async def test_returns_none_when_not_yet_captured(self):
        svc, odds_repo, _ = _make_service()
        odds_repo.get_closing_snapshot.return_value = None

        result = await svc.get_closing_snapshot(uuid.uuid4(), uuid.uuid4())

        assert result is None


class TestGetHistory:
    async def test_defaults_forwarded(self):
        svc, odds_repo, _ = _make_service()
        match_id = uuid.uuid4()
        odds_repo.get_history.return_value = []

        await svc.get_history(match_id)

        odds_repo.get_history.assert_awaited_once_with(
            match_id,
            bookmaker_id=None,
            market=OddsMarket.MATCH_WINNER,
            from_time=None,
        )

    async def test_all_params_forwarded(self):
        svc, odds_repo, _ = _make_service()
        match_id = uuid.uuid4()
        book_id = uuid.uuid4()
        from_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        odds_repo.get_history.return_value = []

        await svc.get_history(
            match_id,
            bookmaker_id=book_id,
            market=OddsMarket.OVER_UNDER,
            from_time=from_time,
        )

        odds_repo.get_history.assert_awaited_once_with(
            match_id,
            bookmaker_id=book_id,
            market=OddsMarket.OVER_UNDER,
            from_time=from_time,
        )

    async def test_returns_repo_result(self):
        svc, odds_repo, _ = _make_service()
        snapshots = [_fake_snapshot(), _fake_snapshot()]
        odds_repo.get_history.return_value = snapshots

        result = await svc.get_history(uuid.uuid4())

        assert result is snapshots


class TestGetBookmaker:
    async def test_delegates_to_bookmaker_repo(self):
        svc, _, book_repo = _make_service()
        book = _fake_bookmaker()
        book_repo.get_by_id_or_raise.return_value = book

        result = await svc.get_bookmaker(book.id)

        book_repo.get_by_id_or_raise.assert_awaited_once_with(book.id)
        assert result is book

    async def test_propagates_lookup_error(self):
        svc, _, book_repo = _make_service()
        book_repo.get_by_id_or_raise.side_effect = LookupError

        with pytest.raises(LookupError):
            await svc.get_bookmaker(uuid.uuid4())


class TestGetBookmakerBySlug:
    async def test_delegates_to_bookmaker_repo(self):
        svc, _, book_repo = _make_service()
        book = _fake_bookmaker()
        book_repo.get_by_slug.return_value = book

        result = await svc.get_bookmaker_by_slug("bet365")

        book_repo.get_by_slug.assert_awaited_once_with("bet365")
        assert result is book

    async def test_returns_none_when_not_found(self):
        svc, _, book_repo = _make_service()
        book_repo.get_by_slug.return_value = None

        result = await svc.get_bookmaker_by_slug("unknown")

        assert result is None


class TestListActiveBookmakers:
    async def test_delegates_to_bookmaker_repo(self):
        svc, _, book_repo = _make_service()
        books = [_fake_bookmaker("Bet365"), _fake_bookmaker("Betfair")]
        book_repo.get_active.return_value = books

        result = await svc.list_active_bookmakers()

        book_repo.get_active.assert_awaited_once()
        assert result is books
