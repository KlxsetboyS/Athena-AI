"""CompetitionService – orchestrates CompetitionRepository.

Responsibilities
----------------
- Retrieve individual competitions by ID or external ID.
- List competitions with optional filters (type, country).

No business logic lives here yet; Sprint 2.x will add validation
and domain events.  The service is the single entry point for any
caller that needs competition data, insulating them from the
repository interface.
"""
from __future__ import annotations

import uuid
from typing import Sequence

from athena.db.enums import CompetitionType
from athena.db.models.competition import Competition
from athena.repositories.competition import CompetitionRepository


class CompetitionService:
    """Service layer for Competition domain operations.

    Args:
        repository: Injected :class:`CompetitionRepository`.
    """

    def __init__(self, repository: CompetitionRepository) -> None:
        self._repo = repository

    # ── Lookups ───────────────────────────────────────────────────────────────

    async def get_competition(self, competition_id: uuid.UUID) -> Competition:
        """Return a competition by primary key.

        Raises:
            LookupError: If no active competition with *competition_id* exists.
        """
        return await self._repo.get_by_id_or_raise(competition_id)

    async def get_by_external_id(self, external_id: str) -> Competition | None:
        """Return a competition by provider external ID, or ``None``."""
        return await self._repo.get_by_external_id(external_id)

    # ── Listings ──────────────────────────────────────────────────────────────

    async def list_competitions(
        self,
        *,
        competition_type: CompetitionType | None = None,
        country_code: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[Competition]:
        """Return competitions with optional filters.

        Args:
            competition_type: Filter by league, cup, etc. (optional).
            country_code:     ISO 3166-1 alpha-3 country filter (optional).
            offset:           Pagination offset.
            limit:            Maximum rows to return.
        """
        if competition_type is not None:
            return await self._repo.get_by_type(
                competition_type, country_code=country_code
            )
        if country_code is not None:
            return await self._repo.get_by_country(country_code)
        return await self._repo.list(offset=offset, limit=limit)
