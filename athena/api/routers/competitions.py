"""REST endpoints for Competition."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from athena.api.deps import get_competition_service, get_season_service
from athena.api.schemas.competition import CompetitionOut
from athena.api.schemas.season import SeasonOut
from athena.db.enums import CompetitionType
from athena.services.competition_service import CompetitionService
from athena.services.season_service import SeasonService

router = APIRouter(prefix="/competitions", tags=["competitions"])


@router.get("", response_model=list[CompetitionOut])
async def list_competitions(
    competition_type: CompetitionType | None = Query(None, description="Filter by type"),
    country_code: str | None = Query(None, description="ISO 3166-1 alpha-3 country code"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    svc: CompetitionService = Depends(get_competition_service),
) -> list[CompetitionOut]:
    """Return a list of competitions with optional filters."""
    items = await svc.list_competitions(
        competition_type=competition_type,
        country_code=country_code,
        offset=offset,
        limit=limit,
    )
    return [CompetitionOut.model_validate(c) for c in items]


@router.get("/{competition_id}", response_model=CompetitionOut)
async def get_competition(
    competition_id: uuid.UUID,
    svc: CompetitionService = Depends(get_competition_service),
) -> CompetitionOut:
    """Return a single competition by ID. Returns 404 if not found."""
    comp = await svc.get_competition(competition_id)
    return CompetitionOut.model_validate(comp)


@router.get("/{competition_id}/seasons", response_model=list[SeasonOut])
async def list_competition_seasons(
    competition_id: uuid.UUID,
    svc: SeasonService = Depends(get_season_service),
) -> list[SeasonOut]:
    """Return all seasons for a competition, newest first."""
    items = await svc.list_seasons(competition_id)
    return [SeasonOut.model_validate(s) for s in items]
