"""REST endpoints for Odds (snapshots, bookmakers)."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query

from athena.api.deps import get_odds_service
from athena.api.schemas.odds import BookmakerOut, OddsSnapshotOut
from athena.db.enums import OddsMarket
from athena.services.odds_service import OddsService

router = APIRouter(tags=["odds"])

# ── Bookmakers ────────────────────────────────────────────────────────────────

bookmaker_router = APIRouter(prefix="/bookmakers", tags=["bookmakers"])


@bookmaker_router.get("", response_model=list[BookmakerOut])
async def list_active_bookmakers(
    svc: OddsService = Depends(get_odds_service),
) -> list[BookmakerOut]:
    """Return all active bookmakers."""
    books = await svc.list_active_bookmakers()
    return [BookmakerOut.model_validate(b) for b in books]


@bookmaker_router.get("/{bookmaker_id}", response_model=BookmakerOut)
async def get_bookmaker(
    bookmaker_id: uuid.UUID,
    svc: OddsService = Depends(get_odds_service),
) -> BookmakerOut:
    """Return a bookmaker by ID. Returns 404 if not found."""
    book = await svc.get_bookmaker(bookmaker_id)
    return BookmakerOut.model_validate(book)


# ── Match-scoped odds ─────────────────────────────────────────────────────────

match_odds_router = APIRouter(prefix="/matches/{match_id}/odds", tags=["odds"])


@match_odds_router.get("/latest", response_model=OddsSnapshotOut)
async def get_latest_odds(
    match_id: uuid.UUID,
    bookmaker_id: uuid.UUID = Query(...),
    market: OddsMarket = Query(OddsMarket.MATCH_WINNER),
    svc: OddsService = Depends(get_odds_service),
) -> OddsSnapshotOut:
    """Return the most recently captured odds snapshot for a match/bookmaker pair.

    Returns 404 if no snapshot exists.
    """
    snap = await svc.get_latest_snapshot(match_id, bookmaker_id, market)
    if snap is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No odds snapshot found")
    return OddsSnapshotOut.model_validate(snap)


@match_odds_router.get("/closing", response_model=OddsSnapshotOut)
async def get_closing_odds(
    match_id: uuid.UUID,
    bookmaker_id: uuid.UUID = Query(...),
    market: OddsMarket = Query(OddsMarket.MATCH_WINNER),
    svc: OddsService = Depends(get_odds_service),
) -> OddsSnapshotOut:
    """Return the closing-line odds snapshot. Returns 404 if not yet captured."""
    snap = await svc.get_closing_snapshot(match_id, bookmaker_id, market)
    if snap is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="No closing-line snapshot found")
    return OddsSnapshotOut.model_validate(snap)


@match_odds_router.get("/history", response_model=list[OddsSnapshotOut])
async def get_odds_history(
    match_id: uuid.UUID,
    bookmaker_id: uuid.UUID | None = Query(None),
    market: OddsMarket = Query(OddsMarket.MATCH_WINNER),
    from_time: datetime | None = Query(None),
    svc: OddsService = Depends(get_odds_service),
) -> list[OddsSnapshotOut]:
    """Return full odds history for a match, oldest first."""
    snaps = await svc.get_history(
        match_id,
        bookmaker_id=bookmaker_id,
        market=market,
        from_time=from_time,
    )
    return [OddsSnapshotOut.model_validate(s) for s in snaps]
