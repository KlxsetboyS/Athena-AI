"""Pydantic schemas for Team."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from athena.db.enums import TeamGender


class TeamOut(BaseModel):
    """Read schema for Team."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    short_name: str | None
    country_code: str | None
    gender: TeamGender
    external_id: str | None
    created_at: datetime
    updated_at: datetime
