"""Pydantic schemas for Match."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from athena.db.enums import MatchStatus


class MatchOut(BaseModel):
    """Read schema for Match."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    competition_id: uuid.UUID
    season_id: uuid.UUID
    home_team_id: uuid.UUID
    away_team_id: uuid.UUID
    kickoff_time_utc: datetime
    venue: str | None
    matchday: int | None
    status: MatchStatus
    external_id: str | None
    created_at: datetime
    updated_at: datetime
