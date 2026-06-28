"""MatchRepository – domain-specific queries for Match.

This repository is the most query-intensive in the platform.  It is used by:
- Data ingestion: upsert matches from external providers
- Feature engineering: load match windows for a team/competition
- Inference: retrieve upcoming matches for prediction
- API: serve match listings with filters
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Sequence

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import selectinload

from athena.db.enums import MatchStatus
from athena.db.models.match import Match
from athena.db.models.match_result import MatchResult
from athena.repositories.base import BaseRepository

# Statuses that represent a completed, usable match for ML purposes
USABLE_STATUSES = (MatchStatus.FINISHED,)

# Statuses that represent an upcoming/live match
PENDING_STATUSES = (MatchStatus.SCHEDULED, MatchStatus.LIVE, MatchStatus.HALF_TIME)


class MatchRepository(BaseRepository[Match]):
    """Repository for :class:`~athena.db.models.match.Match`."""

    model = Match

    # ── Lookup helpers ────────────────────────────────────────────────────────

    async def get_by_external_id(self, external_id: str) -> Match | None:
        """Return a match by provider external ID, or ``None``."""
        stmt = (
            select(Match)
            .where(Match.external_id == external_id)
            .where(Match.is_deleted.is_(False))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_result(self, match_id: uuid.UUID) -> Match | None:
        """Return a match with its result eagerly loaded."""
        stmt = (
            select(Match)
            .where(Match.id == match_id)
            .where(Match.is_deleted.is_(False))
            .options(selectinload(Match.result))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_odds(self, match_id: uuid.UUID) -> Match | None:
        """Return a match with all odds snapshots (and their selections) eagerly loaded."""
        from athena.db.models.odds_snapshot import OddsSnapshot  # local import avoids cycle

        stmt = (
            select(Match)
            .where(Match.id == match_id)
            .where(Match.is_deleted.is_(False))
            .options(
                selectinload(Match.odds_snapshots).selectinload(OddsSnapshot.selections)
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ── Date-based queries ────────────────────────────────────────────────────

    async def get_by_date(
        self,
        date_from: datetime,
        date_to: datetime,
        *,
        competition_id: uuid.UUID | None = None,
    ) -> Sequence[Match]:
        """Return matches with kickoff between *date_from* and *date_to* (UTC).

        Args:
            date_from:      Start of the time window (inclusive).
            date_to:        End of the time window (inclusive).
            competition_id: Optionally restrict to a single competition.
        """
        stmt = (
            select(Match)
            .where(Match.kickoff_time_utc >= date_from)
            .where(Match.kickoff_time_utc <= date_to)
            .where(Match.is_deleted.is_(False))
        )
        if competition_id is not None:
            stmt = stmt.where(Match.competition_id == competition_id)
        stmt = stmt.order_by(Match.kickoff_time_utc)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    # ── Competition / season queries ──────────────────────────────────────────

    async def get_by_competition(
        self,
        competition_id: uuid.UUID,
        *,
        season_id: uuid.UUID | None = None,
    ) -> Sequence[Match]:
        """Return all matches for a competition, optionally scoped to a season."""
        stmt = (
            select(Match)
            .where(Match.competition_id == competition_id)
            .where(Match.is_deleted.is_(False))
        )
        if season_id is not None:
            stmt = stmt.where(Match.season_id == season_id)
        stmt = stmt.order_by(Match.kickoff_time_utc)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    # ── Team queries ──────────────────────────────────────────────────────────

    async def get_by_team(
        self,
        team_id: uuid.UUID,
        *,
        season_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> Sequence[Match]:
        """Return matches involving *team_id* (home or away), newest first.

        Args:
            team_id:   The team UUID.
            season_id: Optionally restrict to a single season.
            limit:     Maximum number of matches to return.
        """
        stmt = (
            select(Match)
            .where(
                or_(
                    Match.home_team_id == team_id,
                    Match.away_team_id == team_id,
                )
            )
            .where(Match.is_deleted.is_(False))
        )
        if season_id is not None:
            stmt = stmt.where(Match.season_id == season_id)
        stmt = stmt.order_by(Match.kickoff_time_utc.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_head_to_head(
        self,
        team_a_id: uuid.UUID,
        team_b_id: uuid.UUID,
        *,
        limit: int = 10,
    ) -> Sequence[Match]:
        """Return H2H matches between two teams (any home/away combination), newest first."""
        stmt = (
            select(Match)
            .where(
                or_(
                    and_(
                        Match.home_team_id == team_a_id,
                        Match.away_team_id == team_b_id,
                    ),
                    and_(
                        Match.home_team_id == team_b_id,
                        Match.away_team_id == team_a_id,
                    ),
                )
            )
            .where(Match.is_deleted.is_(False))
            .order_by(Match.kickoff_time_utc.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    # ── Status-based queries ──────────────────────────────────────────────────

    async def get_upcoming(
        self,
        *,
        competition_id: uuid.UUID | None = None,
        from_time: datetime | None = None,
        limit: int = 50,
    ) -> Sequence[Match]:
        """Return scheduled/live matches ordered by kickoff ascending.

        Args:
            competition_id: Optionally scope to one competition.
            from_time:      Lower bound for kickoff (defaults to now if None).
            limit:          Maximum rows.
        """
        stmt = (
            select(Match)
            .where(Match.status.in_(PENDING_STATUSES))
            .where(Match.is_deleted.is_(False))
        )
        if competition_id is not None:
            stmt = stmt.where(Match.competition_id == competition_id)
        if from_time is not None:
            stmt = stmt.where(Match.kickoff_time_utc >= from_time)
        stmt = stmt.order_by(Match.kickoff_time_utc).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_finished(
        self,
        *,
        competition_id: uuid.UUID | None = None,
        season_id: uuid.UUID | None = None,
        limit: int = 100,
    ) -> Sequence[Match]:
        """Return finished matches (usable for ML), newest first.

        Excludes cancelled, postponed, abandoned and awarded matches.
        """
        stmt = (
            select(Match)
            .where(Match.status.in_(USABLE_STATUSES))
            .where(Match.is_deleted.is_(False))
        )
        if competition_id is not None:
            stmt = stmt.where(Match.competition_id == competition_id)
        if season_id is not None:
            stmt = stmt.where(Match.season_id == season_id)
        stmt = stmt.order_by(Match.kickoff_time_utc.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_without_result(
        self,
        *,
        competition_id: uuid.UUID | None = None,
    ) -> Sequence[Match]:
        """Return finished matches that have no associated MatchResult yet.

        Used by the result-ingestion pipeline to identify gaps.
        """
        stmt = (
            select(Match)
            .outerjoin(MatchResult, MatchResult.match_id == Match.id)
            .where(Match.status == MatchStatus.FINISHED)
            .where(Match.is_deleted.is_(False))
            .where(MatchResult.id.is_(None))
        )
        if competition_id is not None:
            stmt = stmt.where(Match.competition_id == competition_id)
        result = await self._session.execute(stmt)
        return result.scalars().all()
