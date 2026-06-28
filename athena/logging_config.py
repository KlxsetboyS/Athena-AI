"""Structured logging configuration for Athena AI.

Configures both the stdlib ``logging`` module and ``structlog`` so that:
- All ``logging.getLogger(...)`` calls (including SQLAlchemy) are captured.
- Output is either human-readable text (development) or newline-delimited
  JSON (production / log aggregation).
- A ``request_id`` field is automatically added to every log record when
  the athena.context ContextVar is set.

Usage::

    from athena.logging_config import configure_logging
    configure_logging(level="INFO", fmt="json")

Called once at application startup (inside the lifespan context manager).
Safe to call multiple times – structlog is idempotent on re-configuration.
"""
from __future__ import annotations

import logging
import logging.config
import sys
from typing import Any

import structlog

# Direct import — athena.context has no FastAPI dependency, so this is safe
# from any layer including providers.
from athena.context import get_request_id


def _request_id_processor(
    logger: Any, method: str, event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Inject the current request_id (if any) into every log record."""
    rid = get_request_id()
    if rid:
        event_dict["request_id"] = rid
    return event_dict


def configure_logging(level: str = "INFO", fmt: str = "text") -> None:
    """Configure stdlib logging and structlog.

    Args:
        level: Logging level string (``"DEBUG"``, ``"INFO"``, etc.).
        fmt:   Output format — ``"text"`` for development, ``"json"`` for
               production / log aggregation pipelines.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # ── Shared processors (run for every log record) ──────────────────────────
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        _request_id_processor,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if fmt == "json":
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Route stdlib logging through structlog for consistent formatting
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(numeric_level)

    # Quieten noisy libraries
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if level == "DEBUG" else logging.WARNING
    )
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
