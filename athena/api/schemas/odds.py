"""Pydantic schemas for Bookmaker, OddsSnapshot, OddsSelection."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from athena.db.enums import OddsFormat, OddsMarket, SelectionType


class BookmakerOut(BaseModel):
    """Read schema for Bookmaker."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    country_code: str | None
    is_exchange: bool
    is_active: bool
    external_id: str | None
    created_at: datetime
    updated_at: datetime


class OddsSelectionOut(BaseModel):
    """Read schema for OddsSelection (a single outcome's odds)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    selection_type: SelectionType
    label: str | None
    decimal_odd: Decimal
    line: Decimal | None
    is_suspended: bool


class OddsSnapshotOut(BaseModel):
    """Read schema for OddsSnapshot, including its selections."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    match_id: uuid.UUID
    bookmaker_id: uuid.UUID
    market: OddsMarket
    odds_format: OddsFormat
    captured_at: datetime
    is_closing: bool
    source: str
    external_ref: str | None
    selections: list[OddsSelectionOut]
    created_at: datetime
    updated_at: datetime
