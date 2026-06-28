"""REST endpoints for Team."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from athena.api.deps import get_team_service
from athena.api.schemas.team import TeamOut
from athena.services.team_service import TeamService

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("", response_model=list[TeamOut])
async def search_teams(
    q: str = Query(..., min_length=2, description="Name fragment to search for"),
    svc: TeamService = Depends(get_team_service),
) -> list[TeamOut]:
    """Case-insensitive partial search across team names."""
    teams = await svc.search_team(q)
    return [TeamOut.model_validate(t) for t in teams]


@router.get("/{team_id}", response_model=TeamOut)
async def get_team(
    team_id: uuid.UUID,
    svc: TeamService = Depends(get_team_service),
) -> TeamOut:
    """Return a single team by ID. Returns 404 if not found."""
    team = await svc.get_team(team_id)
    return TeamOut.model_validate(team)
