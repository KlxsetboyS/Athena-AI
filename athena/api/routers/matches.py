"""REST endpoints for Match."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query

from athena.api.deps import get_match_service
from athena.api.schemas.match import MatchOut
from athena.services.match_service import MatchService

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("/upcoming", response_model=list[MatchOut])
async def get_upcoming_matches(
    competition_id: uuid.UUID | None = Query(None),
    from_time: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    svc: MatchService = Depends(get_match_service),
) -> list[MatchOut]:
    """Return scheduled/live matches ordered by kickoff ascending."""
    matches = await svc.get_upcoming_matches(
        competition_id=competition_id,
        from_time=from_time,
        limit=limit,
    )
    return [MatchOut.model_validate(m) for m in matches]


@router.get("/finished", response_model=list[MatchOut])
async def get_finished_matches(
    competition_id: uuid.UUID | None = Query(None),
    season_id: uuid.UUID | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    svc: MatchService = Depends(get_match_service),
) -> list[MatchOut]:
    """Return finished matches usable for ML, newest first."""
    matches = await svc.get_finished_matches(
        competition_id=competition_id,
        season_id=season_id,
        limit=limit,
    )
    return [MatchOut.model_validate(m) for m in matches]


@router.get("/{match_id}", response_model=MatchOut)
async def get_match(
    match_id: uuid.UUID,
    svc: MatchService = Depends(get_match_service),
) -> MatchOut:
    """Return a single match by ID. Returns 404 if not found."""
    match = await svc.get_match(match_id)
    return MatchOut.model_validate(match)


@router.get("/{match_id}/history", response_model=list[MatchOut])
async def get_team_history_for_match(
    match_id: uuid.UUID,
    team_id: uuid.UUID = Query(..., description="Team UUID to fetch history for"),
    limit: int = Query(10, ge=1, le=50),
    svc: MatchService = Depends(get_match_service),
) -> list[MatchOut]:
    """Return recent matches for a team (used for pre-match context)."""
    # Validate the match exists first
    await svc.get_match(match_id)
    matches = await svc.get_match_history(team_id, limit=limit)
    return [MatchOut.model_validate(m) for m in matches]
