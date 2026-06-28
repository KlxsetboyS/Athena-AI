"""Request ID middleware for Athena AI.

Assigns a unique correlation ID to every incoming HTTP request so that all
log lines produced during that request share the same ``request_id`` field.

How it works
------------
1. The middleware reads the configurable request-ID header from the incoming
   request (default: ``X-Request-ID``).
2. If the header is absent, a UUID4 is generated.
3. The ID is stored in a ContextVar (via ``athena.context``) for the duration
   of the request, making it accessible to any code in the call-stack
   (including structlog processors and ProviderClient log calls).
4. The ID is echoed back in the response header so callers can correlate
   their own logs with Athena's.

The middleware is a plain ASGI callable (not a Starlette BaseHTTPMiddleware
subclass) to avoid the double-exception-wrapping issue present in some
Starlette versions.

Backward compatibility
----------------------
``get_request_id`` is re-exported from this module so that existing imports
from ``athena.api.middleware`` continue to work unchanged.
"""
from __future__ import annotations

import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

# ContextVar lives in athena.context — no FastAPI dependency there.
# Re-exported here for backward compatibility with any code that imports
# get_request_id from this module.
from athena.context import get_request_id, reset_request_id, set_request_id

__all__ = ["RequestIDMiddleware", "get_request_id"]


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

        # Store in ContextVar via athena.context — visible to all coroutines
        token = set_request_id(request_id)

        async def send_with_header(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers_list = list(message.get("headers", []))
                headers_list.append(
                    (self.header_name, request_id.encode())
                )
                message = {**message, "headers": headers_list}
            await send(message)

        try:
            await self.app(scope, receive, send_with_header)
        finally:
            # Reset ContextVar so it doesn't leak across requests
            reset_request_id(token)
