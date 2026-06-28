"""REST endpoints for Season."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from athena.api.deps import get_season_service, get_team_service
from athena.api.schemas.season import SeasonOut
from athena.api.schemas.team import TeamOut
from athena.services.season_service import SeasonService
from athena.services.team_service import TeamService

router = APIRouter(prefix="/seasons", tags=["seasons"])


@router.get("/{season_id}", response_model=SeasonOut)
async def get_season(
    season_id: uuid.UUID,
    svc: SeasonService = Depends(get_season_service),
) -> SeasonOut:
    """Return a single season by ID. Returns 404 if not found."""
    season = await svc.get_season(season_id)
    return SeasonOut.model_validate(season)


@router.get("/{season_id}/teams", response_model=list[TeamOut])
async def list_season_teams(
    season_id: uuid.UUID,
    season_svc: SeasonService = Depends(get_season_service),
    team_svc: TeamService = Depends(get_team_service),
) -> list[TeamOut]:
    """Return all teams registered for a season. Returns 404 if season not found."""
    await season_svc.get_season(season_id)  # validates existence → 404 if not found
    teams = await team_svc.list_teams_in_season(season_id)
    return [TeamOut.model_validate(t) for t in teams]
