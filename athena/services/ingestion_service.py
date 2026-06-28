"""IngestionService — orchestrates provider data into the repository layer.

Responsibilities
----------------
- Call a provider to fetch external data (competitions, matches, odds).
- For each DTO received, check if the entity already exists (by external_id).
- Create it if new; update it if changed.
- Log the result of each ingestión run.

What IngestionService does NOT do
----------------------------------
- HTTP — that is ProviderClient's job.
- JSON parsing — that is the mapper's job.
- Business rule validation — that belongs to future Sprint 2.x.

RepositoryBundle
-----------------
Groups the six repositories needed for ingestión into a single dataclass
so that ``IngestionService.__init__`` receives two arguments instead of
seven, while remaining explicit and testable.

Usage::

    repos = RepositoryBundle(
        competitions=CompetitionRepository(session),
        seasons=SeasonRepository(session),
        teams=TeamRepository(session),
        matches=MatchRepository(session),
        odds=OddsRepository(session),
        bookmakers=BookmakerRepository(session),
    )
    service = IngestionService(provider, repos)
    result = await service.ingest_competitions()
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from athena.providers.base import BaseProvider
from athena.providers.exceptions import ProviderError
from athena.providers.models import (
    CompetitionDTO,
    MatchDTO,
    OddsSnapshotDTO,
)
from athena.repositories.competition import CompetitionRepository
from athena.repositories.match import MatchRepository
from athena.repositories.odds import BookmakerRepository, OddsRepository
from athena.repositories.season import SeasonRepository
from athena.repositories.team import TeamRepository

logger = logging.getLogger(__name__)


@dataclass
class RepositoryBundle:
    """Thin grouping of all repositories needed for data ingestión.

    Attributes:
        competitions: :class:`CompetitionRepository`
        seasons:      :class:`SeasonRepository`
        teams:        :class:`TeamRepository`
        matches:      :class:`MatchRepository`
        odds:         :class:`OddsRepository`
        bookmakers:   :class:`BookmakerRepository`
    """

    competitions: CompetitionRepository
    seasons: SeasonRepository
    teams: TeamRepository
    matches: MatchRepository
    odds: OddsRepository
    bookmakers: BookmakerRepository


@dataclass
class IngestionResult:
    """Summary of one ingestión run."""

    entity: str
    provider: str
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0

    def __str__(self) -> str:
        return (
            f"[{self.provider}/{self.entity}] "
            f"created={self.created} updated={self.updated} "
            f"skipped={self.skipped} errors={self.errors}"
        )


class IngestionService:
    """Orchestrate ingestión of provider data into the repository layer.

    Args:
        provider: Any :class:`BaseProvider` implementation.
        repos:    :class:`RepositoryBundle` with all required repositories.
    """

    def __init__(self, provider: BaseProvider, repos: RepositoryBundle) -> None:
        self._provider = provider
        self._repos = repos

    # ── Public ingestión methods ──────────────────────────────────────────────

    async def ingest_competitions(
        self,
        *,
        country_code: str | None = None,
    ) -> IngestionResult:
        """Fetch and upsert competitions from the provider.

        Args:
            country_code: Optional ISO 3166-1 alpha-3 filter forwarded to
                          the provider.

        Returns:
            :class:`IngestionResult` with counts of created/updated/errors.
        """
        result = IngestionResult(
            entity="competitions", provider=self._provider.name
        )

        try:
            dtos = await self._provider.get_competitions(country_code=country_code)
        except ProviderError as exc:
            logger.error(
                "ingestión failed",
                extra={"entity": "competitions", "error": str(exc)},
            )
            result.errors += 1
            return result

        for dto in dtos:
            try:
                await self._upsert_competition(dto, result)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "competition upsert failed",
                    extra={"external_id": dto.external_id, "error": str(exc)},
                )
                result.errors += 1

        logger.info("ingestión complete", extra={"summary": str(result)})
        return result

    async def ingest_matches(
        self,
        competition_external_id: str,
        *,
        season_external_id: str | None = None,
    ) -> IngestionResult:
        """Fetch and upsert matches for a competition.

        Args:
            competition_external_id: Provider-side competition identifier.
            season_external_id:      Optional season filter.
        """
        result = IngestionResult(entity="matches", provider=self._provider.name)

        try:
            dtos = await self._provider.get_matches(
                competition_external_id,
                season_external_id=season_external_id,
            )
        except ProviderError as exc:
            logger.error(
                "ingestión failed",
                extra={"entity": "matches", "error": str(exc)},
            )
            result.errors += 1
            return result

        for dto in dtos:
            try:
                await self._upsert_match(dto, result)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "match upsert failed",
                    extra={"external_id": dto.external_id, "error": str(exc)},
                )
                result.errors += 1

        logger.info("ingestión complete", extra={"summary": str(result)})
        return result

    async def ingest_odds(
        self,
        match_external_id: str,
    ) -> IngestionResult:
        """Fetch and store odds snapshots for a match.

        Odds snapshots are immutable by design — we only create, never update.

        Args:
            match_external_id: Provider-side match identifier.
        """
        result = IngestionResult(entity="odds", provider=self._provider.name)

        try:
            dtos = await self._provider.get_odds(match_external_id)
        except ProviderError as exc:
            logger.error(
                "ingestión failed",
                extra={"entity": "odds", "error": str(exc)},
            )
            result.errors += 1
            return result

        for dto in dtos:
            try:
                await self._create_odds_snapshot(dto, result)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "odds snapshot upsert failed",
                    extra={"external_ref": dto.external_ref, "error": str(exc)},
                )
                result.errors += 1

        logger.info("ingestión complete", extra={"summary": str(result)})
        return result

    # ── Private upsert helpers ────────────────────────────────────────────────

    async def _upsert_competition(
        self, dto: CompetitionDTO, result: IngestionResult
    ) -> None:
        """Create or update a Competition from a DTO."""
        existing = await self._repos.competitions.get_by_external_id(
            dto.external_id
        )
        if existing is None:
            await self._repos.competitions.create(
                external_id=dto.external_id,
                name=dto.name,
                country_code=dto.country_code,
                competition_type=dto.competition_type,
                gender=dto.gender,
            )
            result.created += 1
        else:
            # Update only if name or country changed
            if existing.name != dto.name or existing.country_code != dto.country_code:
                await self._repos.competitions.update(
                    existing,
                    name=dto.name,
                    country_code=dto.country_code,
                )
                result.updated += 1
            else:
                result.skipped += 1

    async def _upsert_match(
        self, dto: MatchDTO, result: IngestionResult
    ) -> None:
        """Create or update a Match from a DTO.

        Note: Match creation requires competition_id, season_id, home_team_id,
        and away_team_id as UUIDs — these must be resolved from external_ids
        before creation.  If any resolution fails, the match is skipped.
        """
        existing = await self._repos.matches.get_by_external_id(dto.external_id)
        if existing is None:
            # Resolve FK UUIDs from external IDs
            competition = await self._repos.competitions.get_by_external_id(
                dto.competition_external_id
            )
            if competition is None:
                logger.debug(
                    "match skipped: competition not found",
                    extra={"competition_ext_id": dto.competition_external_id},
                )
                result.skipped += 1
                return

            home_team = await self._repos.teams.get_by_external_id(
                dto.home_team_external_id
            )
            away_team = await self._repos.teams.get_by_external_id(
                dto.away_team_external_id
            )
            if home_team is None or away_team is None:
                logger.debug(
                    "match skipped: team not found",
                    extra={"home": dto.home_team_external_id,
                           "away": dto.away_team_external_id},
                )
                result.skipped += 1
                return

            await self._repos.matches.create(
                external_id=dto.external_id,
                competition_id=competition.id,
                season_id=competition.id,  # placeholder until season resolution
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                kickoff_time_utc=dto.kickoff_time_utc,
                venue=dto.venue,
                matchday=dto.matchday,
                status=dto.status,
            )
            result.created += 1
        else:
            # Update status if it has changed
            if existing.status != dto.status:
                await self._repos.matches.update(existing, status=dto.status)
                result.updated += 1
            else:
                result.skipped += 1

    async def _create_odds_snapshot(
        self, dto: OddsSnapshotDTO, result: IngestionResult
    ) -> None:
        """Create an odds snapshot if it doesn't already exist (by external_ref)."""
        if dto.external_ref:
            exists = await self._repos.odds.snapshot_exists(dto.external_ref)
            if exists:
                result.skipped += 1
                return

        # Resolve bookmaker — create if not found
        bookmaker = await self._repos.bookmakers.get_by_slug(dto.bookmaker_slug)
        if bookmaker is None:
            bookmaker = await self._repos.bookmakers.create(
                name=dto.bookmaker_name,
                slug=dto.bookmaker_slug,
            )

        # Resolve match by external_id
        match = await self._repos.matches.get_by_external_id(dto.match_external_id)
        if match is None:
            logger.debug(
                "odds snapshot skipped: match not found",
                extra={"match_external_id": dto.match_external_id},
            )
            result.skipped += 1
            return

        await self._repos.odds.create(
            match_id=match.id,
            bookmaker_id=bookmaker.id,
            market=dto.market,
            captured_at=dto.captured_at,
            is_closing=dto.is_closing,
            source=dto.source,
            external_ref=dto.external_ref,
        )
        result.created += 1
