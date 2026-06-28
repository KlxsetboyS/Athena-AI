"""Shared async context variables for Athena AI.

This module is the single source of truth for per-request context that must
be accessible across all layers (API middleware, providers, logging).

Design constraints
------------------
- No dependencies on FastAPI, Starlette, or any athena sub-package.
- Safe to import from any layer: api, providers, logging_config.
- Prevents the circular-import chain:
    logging_config → api.middleware → (api package)

Usage
-----
    from athena.context import get_request_id, set_request_id

    # Set (called by RequestIDMiddleware):
    token = set_request_id("abc-123")
    ...
    reset_request_id(token)  # called in finally block

    # Read (called by logging processors, ProviderClient):
    rid = get_request_id()  # "abc-123" or None
"""
from __future__ import annotations

from contextvars import ContextVar, Token

_request_id_var: ContextVar[str | None] = ContextVar(
    "request_id", default=None
)


def get_request_id() -> str | None:
    """Return the request ID for the current async context, or ``None``."""
    return _request_id_var.get()


def set_request_id(request_id: str) -> Token[str | None]:
    """Set the request ID for the current async context.

    Returns the token needed to reset the variable in a ``finally`` block.
    """
    return _request_id_var.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    """Reset the request ID to its previous value using the token."""
    _request_id_var.reset(token)
