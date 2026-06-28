"""Pydantic schemas for Season."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from athena.db.enums import SeasonStatus


class SeasonOut(BaseModel):
    """Read schema for Season."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    competition_id: uuid.UUID
    year_start: int
    year_end: int
    label: str | None
    status: SeasonStatus
    created_at: datetime
    updated_at: datetime
