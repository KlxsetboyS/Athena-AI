"""Shared Pydantic schemas used across all routers."""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Standard error response body."""

    detail: str


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated wrapper for list endpoints."""

    items: list[T]
    total: int
    offset: int
    limit: int
