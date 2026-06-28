"""OddsRepository – queries for Bookmaker, OddsSnapshot and OddsSelection.

Centralises all odds-domain reads so that:
- Feature engineering pulls odds history through one consistent interface.
- The ingestion layer can deduplicate before writing.
- The inference layer can retrieve the latest available odds for a match.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from athena.db.enums import OddsMarket
from athena.db.models.bookmaker import Bookmaker
from athena.db.models.odds_selection import OddsSelection
from athena.db.models.odds_snapshot import OddsSnapshot
from athena.repositories.base import BaseRepository


class BookmakerRepository(BaseRepository[Bookmaker]):
    """Repository for :class:`~athena.db.models.bookmaker.Bookmaker`."""

    model = Bookmaker

    async def get_by_slug(self, slug: str) -> Bookmaker | None:
        """Return a bookmaker by its unique slug, or ``None``."""
        stmt = (
            select(Bookmaker)
            .where(Bookmaker.slug == slug)
            .where(Bookmaker.is_deleted.is_(False))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active(self) -> Sequence[Bookmaker]:
        """Return all active (non-disabled) bookmakers."""
        stmt = (
            select(Bookmaker)
            .where(Bookmaker.is_active.is_(True))
            .where(Bookmaker.is_deleted.is_(False))
            .order_by(Bookmaker.name)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()


class OddsRepository(BaseRepository[OddsSnapshot]):
    """Repository for :class:`~athena.db.models.odds_snapshot.OddsSnapshot`.

    Also provides a convenience accessor for
    :class:`~athena.db.models.odds_selection.OddsSelection` queries.
    """

    model = OddsSnapshot

    # ── Latest / closing snapshots ────────────────────────────────────────────

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
        stmt = (
            select(OddsSnapshot)
            .where(OddsSnapshot.match_id == match_id)
            .where(OddsSnapshot.bookmaker_id == bookmaker_id)
            .where(OddsSnapshot.market == market)
            .where(OddsSnapshot.is_deleted.is_(False))
            .order_by(OddsSnapshot.captured_at.desc())
            .limit(1)
            .options(selectinload(OddsSnapshot.selections))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_closing_snapshot(
        self,
        match_id: uuid.UUID,
        bookmaker_id: uuid.UUID,
        market: OddsMarket = OddsMarket.MATCH_WINNER,
    ) -> OddsSnapshot | None:
        """Return the closing-line snapshot for a match/bookmaker pair, or ``None``.

        The closing line is the odds state immediately before kick-off and is
        widely used as the benchmark for value-betting analysis.
        """
        stmt = (
            select(OddsSnapshot)
            .where(OddsSnapshot.match_id == match_id)
            .where(OddsSnapshot.bookmaker_id == bookmaker_id)
            .where(OddsSnapshot.market == market)
            .where(OddsSnapshot.is_closing.is_(True))
            .where(OddsSnapshot.is_deleted.is_(False))
            .order_by(OddsSnapshot.captured_at.desc())
            .limit(1)
            .options(selectinload(OddsSnapshot.selections))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ── History ───────────────────────────────────────────────────────────────

    async def get_history(
        self,
        match_id: uuid.UUID,
        *,
        bookmaker_id: uuid.UUID | None = None,
        market: OddsMarket = OddsMarket.MATCH_WINNER,
        from_time: datetime | None = None,
    ) -> Sequence[OddsSnapshot]:
        """Return the full odds history for a match, oldest first.

        Each snapshot includes its selections (eager loaded) so callers can
        reconstruct the odds timeline without additional queries.

        Args:
            match_id:     Target match UUID.
            bookmaker_id: Optionally restrict to a single bookmaker.
            market:       Betting market filter.
            from_time:    If set, only return snapshots captured after this time.
        """
        stmt = (
            select(OddsSnapshot)
            .where(OddsSnapshot.match_id == match_id)
            .where(OddsSnapshot.market == market)
            .where(OddsSnapshot.is_deleted.is_(False))
        )
        if bookmaker_id is not None:
            stmt = stmt.where(OddsSnapshot.bookmaker_id == bookmaker_id)
        if from_time is not None:
            stmt = stmt.where(OddsSnapshot.captured_at >= from_time)
        stmt = (
            stmt.order_by(OddsSnapshot.captured_at.asc())
            .options(selectinload(OddsSnapshot.selections))
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_by_bookmaker(
        self,
        bookmaker_id: uuid.UUID,
        *,
        market: OddsMarket = OddsMarket.MATCH_WINNER,
        limit: int = 200,
    ) -> Sequence[OddsSnapshot]:
        """Return recent snapshots for a specific bookmaker, newest first.

        Useful for monitoring a bookmaker's feed or bulk re-processing.
        """
        stmt = (
            select(OddsSnapshot)
            .where(OddsSnapshot.bookmaker_id == bookmaker_id)
            .where(OddsSnapshot.market == market)
            .where(OddsSnapshot.is_deleted.is_(False))
            .order_by(OddsSnapshot.captured_at.desc())
            .limit(limit)
            .options(selectinload(OddsSnapshot.selections))
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_by_external_ref(self, external_ref: str) -> OddsSnapshot | None:
        """Return a snapshot by its provider-side reference (deduplication key)."""
        stmt = (
            select(OddsSnapshot)
            .where(OddsSnapshot.external_ref == external_ref)
            .where(OddsSnapshot.is_deleted.is_(False))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def snapshot_exists(self, external_ref: str) -> bool:
        """Fast existence check by external_ref (avoids loading the full object)."""
        return (await self.get_by_external_ref(external_ref)) is not None

    # ── Selection-level access ────────────────────────────────────────────────

    async def get_selections(
        self, snapshot_id: uuid.UUID
    ) -> Sequence[OddsSelection]:
        """Return all selections for a given snapshot."""
        stmt = (
            select(OddsSelection)
            .where(OddsSelection.snapshot_id == snapshot_id)
            .where(OddsSelection.is_deleted.is_(False))
            .order_by(OddsSelection.selection_type)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()
