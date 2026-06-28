"""MatchService – orchestrates MatchRepository.

Responsibilities
----------------
- Retrieve individual matches (with optional eager loads).
- Query match history for a team (head-to-head, by team, etc.).
- Retrieve upcoming and finished matches with optional filters.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Sequence

from athena.db.models.match import Match
from athena.repositories.match import MatchRepository


class MatchService:
    """Service layer for Match domain operations.

    Args:
        repository: Injected :class:`MatchRepository`.
    """

    def __init__(self, repository: MatchRepository) -> None:
        self._repo = repository

    # ── Lookups ───────────────────────────────────────────────────────────────

    async def get_match(self, match_id: uuid.UUID) -> Match:
        """Return a match by primary key.

        Raises:
            LookupError: If no active match with *match_id* exists.
        """
        return await self._repo.get_by_id_or_raise(match_id)

    async def get_match_with_result(self, match_id: uuid.UUID) -> Match | None:
        """Return a match with its result eagerly loaded, or ``None``."""
        return await self._repo.get_with_result(match_id)

    async def get_match_with_odds(self, match_id: uuid.UUID) -> Match | None:
        """Return a match with all odds snapshots eagerly loaded, or ``None``."""
        return await self._repo.get_with_odds(match_id)

    # ── History queries ───────────────────────────────────────────────────────

    async def get_match_history(
        self,
        team_id: uuid.UUID,
        *,
        season_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> Sequence[Match]:
        """Return recent matches for *team_id* (home or away), newest first.

        Args:
            team_id:   The team to look up.
            season_id: Optionally restrict to a single season.
            limit:     Maximum number of matches to return.
        """
        return await self._repo.get_by_team(
            team_id, season_id=season_id, limit=limit
        )

    async def get_head_to_head(
        self,
        team_a_id: uuid.UUID,
        team_b_id: uuid.UUID,
        *,
        limit: int = 10,
    ) -> Sequence[Match]:
        """Return H2H matches between two teams, newest first.

        Args:
            team_a_id: First team UUID.
            team_b_id: Second team UUID.
            limit:     Maximum rows.
        """
        return await self._repo.get_head_to_head(
            team_a_id, team_b_id, limit=limit
        )

    # ── Status-based listings ─────────────────────────────────────────────────

    async def get_upcoming_matches(
        self,
        *,
        competition_id: uuid.UUID | None = None,
        from_time: datetime | None = None,
        limit: int = 50,
    ) -> Sequence[Match]:
        """Return scheduled/live matches ordered by kickoff ascending.

        Args:
            competition_id: Optionally scope to one competition.
            from_time:      Lower bound for kickoff (defaults to now in repo).
            limit:          Maximum rows.
        """
        return await self._repo.get_upcoming(
            competition_id=competition_id,
            from_time=from_time,
            limit=limit,
        )

    async def get_finished_matches(
        self,
        *,
        competition_id: uuid.UUID | None = None,
        season_id: uuid.UUID | None = None,
        limit: int = 100,
    ) -> Sequence[Match]:
        """Return finished matches usable for ML, newest first.

        Args:
            competition_id: Optionally scope to one competition.
            season_id:      Optionally scope to one season.
            limit:          Maximum rows.
        """
        return await self._repo.get_finished(
            competition_id=competition_id,
            season_id=season_id,
            limit=limit,
        )
