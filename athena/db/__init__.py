"""Athena AI – database layer public API."""
from athena.db.base import Base, metadata
from athena.db.mixins import UUIDMixin, TimestampMixin, SoftDeleteMixin
from athena.db.model import BaseModel
from athena.db.session import (
    build_engine, build_session_factory, get_session, ping,
    build_async_engine, build_async_session_factory, get_async_session, async_ping,
)
from athena.db.enums import (
    CompetitionType, CompetitionGender,
    SeasonStatus,
    TeamGender,
    MatchStatus,
    ResultType, MatchResultStatus,
    OddsMarket, SelectionType, OddsFormat,
)
import athena.db.models  # noqa: F401 – ensures all models are registered

from athena.db.models.competition import Competition
from athena.db.models.season import Season
from athena.db.models.team import Team
from athena.db.models.season_team import SeasonTeam
from athena.db.models.match import Match
from athena.db.models.match_result import MatchResult
from athena.db.models.bookmaker import Bookmaker
from athena.db.models.odds_snapshot import OddsSnapshot
from athena.db.models.odds_selection import OddsSelection

__all__ = [
    # infrastructure
    "Base", "metadata", "BaseModel",
    "UUIDMixin", "TimestampMixin", "SoftDeleteMixin",
    # sync session
    "build_engine", "build_session_factory", "get_session", "ping",
    # async session
    "build_async_engine", "build_async_session_factory", "get_async_session", "async_ping",
    # enums
    "CompetitionType", "CompetitionGender",
    "SeasonStatus",
    "TeamGender",
    "MatchStatus",
    "ResultType", "MatchResultStatus",
    "OddsMarket", "SelectionType", "OddsFormat",
    # models
    "Competition", "Season", "Team", "SeasonTeam",
    "Match", "MatchResult",
    "Bookmaker", "OddsSnapshot", "OddsSelection",
]
