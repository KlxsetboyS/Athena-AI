"""Request ID middleware for Athena AI.

Assigns a unique correlation ID to every incoming HTTP request so that all
log lines produced during that request share the same ``request_id`` field.

How it works
------------
1. The middleware reads the configurable request-ID header from the incoming
   request (default: ``X-Request-ID``).
2. If the header is absent, a UUID4 is generated.
3. The ID is stored in a :mod:`contextvars` ``ContextVar`` for the duration
   of the request, making it accessible to any code in the call-stack
   (including structlog processors and repository log calls).
4. The ID is echoed back in the response header so callers can correlate
   their own logs with Athena's.

The middleware is a plain ASGI callable (not a Starlette BaseHTTPMiddleware
subclass) to avoid the double-exception-wrapping issue present in some
Starlette versions.

Usage::

    app.add_middleware(RequestIDMiddleware, header_name="X-Request-ID")
"""
from __future__ import annotations

import uuid
from contextvars import ContextVar
from typing import Callable

from starlette.types import ASGIApp, Receive, Scope, Send

# ── ContextVar ────────────────────────────────────────────────────────────────

_request_id_var: ContextVar[str | None] = ContextVar(
    "request_id", default=None
)


def get_request_id() -> str | None:
    """Return the request ID for the current async context, or ``None``."""
    return _request_id_var.get()


# ── Middleware ────────────────────────────────────────────────────────────────

class RequestIDMiddleware:
    """ASGI middleware that assigns and propagates a per-request correlation ID.

    Args:
        app:         The wrapped ASGI application.
        header_name: HTTP header used to read/write the request ID.
                     Defaults to ``"X-Request-ID"``.
    """

    def __init__(self, app: ASGIApp, header_name: str = "X-Request-ID") -> None:
        self.app = app
        self.header_name = header_name.lower().encode()  # headers are bytes in ASGI

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        # Extract or generate request ID
        headers = dict(scope.get("headers", []))
        request_id = (
            headers.get(self.header_name, b"").decode() or str(uuid.uuid4())
        )

        # Store in ContextVar — visible to all coroutines in this request
        token = _request_id_var.set(request_id)

        async def send_with_header(message):
            if message["type"] == "http.response.start":
                # Append our header to the response
                headers_list = list(message.get("headers", []))
                headers_list.append(
                    (self.header_name, request_id.encode())
                )
                message = {**message, "headers": headers_list}
            await send(message)

        try:
            await self.app(scope, receive, send_with_header)
        finally:
            # Reset ContextVar so it doesn't leak across requests in the same
            # thread/task (important for test isolation)
            _request_id_var.reset(token)
