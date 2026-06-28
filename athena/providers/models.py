"""Internal Data Transfer Objects (DTOs) for the provider layer.

Design decisions
----------------
- stdlib ``dataclasses`` only — no Pydantic.  DTOs are internal transport
  objects between mappers and IngestionService; they are never serialised
  to JSON or exposed through FastAPI endpoints.
- ``frozen=True`` enforces immutability: once a mapper creates a DTO it
  cannot be accidentally mutated downstream.
- Validation is the mapper's responsibility.  If a mapper produces a DTO,
  the data is already valid for the ingestion layer.
- Enums reuse the existing ``athena.db.enums`` to keep the vocabulary
  consistent across all layers.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from athena.db.enums import (
    CompetitionGender,
    CompetitionType,
    MatchStatus,
    OddsMarket,
    SeasonStatus,
    SelectionType,
    TeamGender,
)


@dataclass(frozen=True)
class CompetitionDTO:
    """Represents a football competition from an external provider."""

    external_id: str
    name: str
    competition_type: CompetitionType
    gender: CompetitionGender
    country_code: str | None = None


@dataclass(frozen=True)
class SeasonDTO:
    """Represents a competition season from an external provider."""

    competition_external_id: str
    year_start: int
    year_end: int
    label: str | None = None
    status: SeasonStatus = SeasonStatus.UPCOMING
    external_id: str | None = None


@dataclass(frozen=True)
class TeamDTO:
    """Represents a football team from an external provider."""

    external_id: str
    name: str
    country_code: str | None = None
    short_name: str | None = None
    gender: TeamGender = TeamGender.MALE


@dataclass(frozen=True)
class MatchDTO:
    """Represents a single match from an external provider."""

    external_id: str
    competition_external_id: str
    home_team_external_id: str
    away_team_external_id: str
    kickoff_time_utc: datetime
    season_external_id: str | None = None
    venue: str | None = None
    matchday: int | None = None
    status: MatchStatus = MatchStatus.SCHEDULED


@dataclass(frozen=True)
class OddsSelectionDTO:
    """A single outcome's odds within a snapshot."""

    selection_type: SelectionType
    decimal_odd: Decimal
    label: str | None = None
    line: Decimal | None = None


@dataclass(frozen=True)
class OddsSnapshotDTO:
    """A frozen record of all odds for one match from one bookmaker."""

    match_external_id: str
    bookmaker_slug: str
    bookmaker_name: str
    market: OddsMarket
    captured_at: datetime
    source: str
    selections: tuple[OddsSelectionDTO, ...]  # tuple for immutability
    is_closing: bool = False
    external_ref: str | None = None
