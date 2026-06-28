"""Pydantic schemas for Competition."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from athena.db.enums import CompetitionGender, CompetitionType


class CompetitionOut(BaseModel):
    """Read schema for Competition — all fields exposed by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    country_code: str | None
    competition_type: CompetitionType
    gender: CompetitionGender
    external_id: str | None
    created_at: datetime
    updated_at: datetime
