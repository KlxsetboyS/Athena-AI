"""Mappers for football-data.org API v4 responses.

All functions are pure: they take a raw dict and return a typed DTO.
They never perform I/O, never access the database, and never mutate input.

Validation strategy
-------------------
- Required fields: accessed directly; ``KeyError`` is caught by the caller
  (``FootballDataProvider``) and re-raised as ``ProviderParseError``.
- Optional fields: accessed via ``.get()`` with ``None`` as default.
- Type coercions: explicit (e.g. ``int(raw["id"])`` for numeric IDs).

Field mapping
-------------
football-data.org uses numeric IDs.  We prefix them with "fd." to make
external_id values namespaced and unambiguous across providers.

Status mapping
--------------
football-data.org statuses → Athena MatchStatus:
    SCHEDULED     → SCHEDULED
    TIMED         → SCHEDULED
    IN_PLAY       → LIVE
    PAUSED        → HALF_TIME
    FINISHED      → FINISHED
    POSTPONED     → POSTPONED
    CANCELLED     → CANCELLED
    SUSPENDED     → CANCELLED  (no direct equivalent)
    AWARDED       → AWARDED
"""
from __future__ import annotations

from athena.db.enums import (
    CompetitionGender,
    CompetitionType,
    MatchStatus,
    SeasonStatus,
    TeamGender,
)
from athena.providers.models import CompetitionDTO, MatchDTO, SeasonDTO, TeamDTO

# ── Status mapping ────────────────────────────────────────────────────────────

_MATCH_STATUS: dict[str, MatchStatus] = {
    "SCHEDULED": MatchStatus.SCHEDULED,
    "TIMED": MatchStatus.SCHEDULED,
    "IN_PLAY": MatchStatus.LIVE,
    "PAUSED": MatchStatus.HALF_TIME,
    "FINISHED": MatchStatus.FINISHED,
    "POSTPONED": MatchStatus.POSTPONED,
    "CANCELLED": MatchStatus.CANCELLED,
    "SUSPENDED": MatchStatus.CANCELLED,
    "AWARDED": MatchStatus.AWARDED,
}

_COMPETITION_TYPE: dict[str, CompetitionType] = {
    "LEAGUE": CompetitionType.LEAGUE,
    "CUP": CompetitionType.CUP,
    "SUPER_CUP": CompetitionType.CUP,
    "PLAYOFFS": CompetitionType.PLAYOFF,
    "INTERNATIONAL": CompetitionType.INTERNATIONAL,
}


# ── Public mapper functions ───────────────────────────────────────────────────

def map_competition(raw: dict) -> CompetitionDTO:
    """Map a single competition object from football-data.org to a DTO.

    Args:
        raw: One entry from ``response["competitions"]``.

    Returns:
        ``CompetitionDTO`` with namespaced ``external_id``.
    """
    area = raw.get("area") or {}
    comp_type_str = raw.get("type", "LEAGUE")
    comp_type = _COMPETITION_TYPE.get(comp_type_str, CompetitionType.LEAGUE)

    return CompetitionDTO(
        external_id=f"fd.{raw['id']}",
        name=raw["name"],
        competition_type=comp_type,
        gender=CompetitionGender.MALE,  # FD does not expose gender; default male
        country_code=area.get("code"),
    )


def map_competitions(raw: dict) -> list[CompetitionDTO]:
    """Map the full competitions list response.

    Args:
        raw: The top-level JSON object with a ``"competitions"`` key.
    """
    return [map_competition(c) for c in raw.get("competitions", [])]


def map_season(raw: dict, competition_external_id: str) -> SeasonDTO:
    """Map a season object nested inside a competition response.

    Args:
        raw:                      Season dict (``currentSeason`` or from seasons list).
        competition_external_id:  External ID of the parent competition.
    """
    start_date = raw.get("startDate", "")
    end_date = raw.get("endDate", "")

    year_start = int(start_date[:4]) if start_date else 0
    year_end = int(end_date[:4]) if end_date else year_start

    winner = raw.get("winner")
    if winner is not None:
        status = SeasonStatus.FINISHED
    elif raw.get("currentMatchday") is not None:
        status = SeasonStatus.ACTIVE
    else:
        status = SeasonStatus.UPCOMING

    label = f"{year_start}/{str(year_end)[-2:]}" if year_start else None

    return SeasonDTO(
        external_id=f"fd.season.{raw['id']}",
        competition_external_id=competition_external_id,
        year_start=year_start,
        year_end=year_end,
        label=label,
        status=status,
    )


def map_team(raw: dict) -> TeamDTO:
    """Map a team object (as it appears inside a match) to a DTO.

    Args:
        raw: Team dict with at minimum ``id`` and ``name``.
    """
    return TeamDTO(
        external_id=f"fd.{raw['id']}",
        name=raw["name"],
        short_name=raw.get("shortName"),
        country_code=None,  # not present in match-embedded team objects
        gender=TeamGender.MALE,
    )


def map_match(raw: dict) -> MatchDTO:
    """Map a single match object from football-data.org to a DTO.

    Args:
        raw: One entry from ``response["matches"]``.
    """
    from datetime import datetime

    competition = raw.get("competition") or {}
    season = raw.get("season") or {}
    home_team = raw["homeTeam"]
    away_team = raw["awayTeam"]

    status_str = raw.get("status", "SCHEDULED")
    status = _MATCH_STATUS.get(status_str, MatchStatus.SCHEDULED)

    utc_date = raw["utcDate"]
    kickoff = datetime.fromisoformat(utc_date.replace("Z", "+00:00"))

    competition_ext_id = f"fd.{competition['id']}" if competition.get("id") else ""
    season_ext_id = f"fd.season.{season['id']}" if season.get("id") else None

    return MatchDTO(
        external_id=f"fd.{raw['id']}",
        competition_external_id=competition_ext_id,
        season_external_id=season_ext_id,
        home_team_external_id=f"fd.{home_team['id']}",
        away_team_external_id=f"fd.{away_team['id']}",
        kickoff_time_utc=kickoff,
        venue=None,  # not present in the matches list endpoint
        matchday=raw.get("matchday"),
        status=status,
    )


def map_matches(raw: dict) -> list[MatchDTO]:
    """Map the full matches list response.

    Args:
        raw: The top-level JSON object with a ``"matches"`` key.
    """
    return [map_match(m) for m in raw.get("matches", [])]
