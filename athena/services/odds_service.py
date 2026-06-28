"""OddsService – orchestrates OddsRepository and BookmakerRepository.

Responsibilities
----------------
- Retrieve the latest and closing-line odds snapshots for a match.
- Retrieve the full odds history with optional filters.
- Look up bookmakers by slug or list active ones.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Sequence

from athena.db.enums import OddsMarket
from athena.db.models.bookmaker import Bookmaker
from athena.db.models.odds_snapshot import OddsSnapshot
from athena.repositories.odds import BookmakerRepository, OddsRepository


class OddsService:
    """Service layer for Odds domain operations.

    Args:
        odds_repository:       Injected :class:`OddsRepository`.
        bookmaker_repository:  Injected :class:`BookmakerRepository`.
    """

    def __init__(
        self,
        odds_repository: OddsRepository,
        bookmaker_repository: BookmakerRepository,
    ) -> None:
        self._odds_repo = odds_repository
        self._bookmaker_repo = bookmaker_repository

    # ── Snapshot lookups ──────────────────────────────────────────────────────

    async def get_latest_snapshot(
        self,
        match_id: uuid.UUID,
        bookmaker_id: uuid.UUID,
        market: OddsMarket = OddsMarket.MATCH_WINNER,
    ) -> OddsSnapshot | None:
        """Return the most recently captured snapshot for a match/bookmaker pair.

        Args:
            match_id:     Target match UUID.
            bookmaker_id: Target bookmaker UUID.
            market:       Betting market (default: MATCH_WINNER / 1X2).
        """
        return await self._odds_repo.get_latest_snapshot(
            match_id, bookmaker_id, market
        )

    async def get_closing_snapshot(
        self,
        match_id: uuid.UUID,
        bookmaker_id: uuid.UUID,
        market: OddsMarket = OddsMarket.MATCH_WINNER,
    ) -> OddsSnapshot | None:
        """Return the closing-line snapshot, or ``None`` if not yet captured.

        Args:
            match_id:     Target match UUID.
            bookmaker_id: Target bookmaker UUID.
            market:       Betting market.
        """
        return await self._odds_repo.get_closing_snapshot(
            match_id, bookmaker_id, market
        )

    # ── History ───────────────────────────────────────────────────────────────

    async def get_history(
        self,
        match_id: uuid.UUID,
        *,
        bookmaker_id: uuid.UUID | None = None,
        market: OddsMarket = OddsMarket.MATCH_WINNER,
        from_time: datetime | None = None,
    ) -> Sequence[OddsSnapshot]:
        """Return full odds history for a match, oldest first.

        Args:
            match_id:     Target match UUID.
            bookmaker_id: Optionally restrict to a single bookmaker.
            market:       Betting market filter.
            from_time:    If set, only return snapshots captured after this time.
        """
        return await self._odds_repo.get_history(
            match_id,
            bookmaker_id=bookmaker_id,
            market=market,
            from_time=from_time,
        )

    # ── Bookmaker helpers ─────────────────────────────────────────────────────

    async def get_bookmaker(self, bookmaker_id: uuid.UUID) -> Bookmaker:
        """Return a bookmaker by primary key.

        Raises:
            LookupError: If no active bookmaker with *bookmaker_id* exists.
        """
        return await self._bookmaker_repo.get_by_id_or_raise(bookmaker_id)

    async def get_bookmaker_by_slug(self, slug: str) -> Bookmaker | None:
        """Return a bookmaker by its unique slug, or ``None``."""
        return await self._bookmaker_repo.get_by_slug(slug)

    async def list_active_bookmakers(self) -> Sequence[Bookmaker]:
        """Return all active (non-disabled) bookmakers."""
        return await self._bookmaker_repo.get_active()
