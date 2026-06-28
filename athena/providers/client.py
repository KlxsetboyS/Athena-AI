"""ProviderClient — shared async HTTP client for provider integrations.

Responsibilities
----------------
- Manage a single ``httpx.AsyncClient`` instance (connection pool reuse).
- Apply timeouts, rate limiting, and retry policy to every request.
- Convert HTTP status codes to typed provider exceptions *before* the
  retry policy sees them.
- Log every request, response, and retry attempt with structlog.
- Expose the current ``request_id`` from ``athena.context`` in log records.

What ProviderClient does NOT do
--------------------------------
- Parse JSON into DTOs — that is the mapper's job.
- Know anything about SQLAlchemy or repositories.
- Understand the semantics of any specific provider's API.

Lifecycle
---------
One ``ProviderClient`` per provider, created during FastAPI lifespan startup
and closed during shutdown.  Never create a client per request.
"""
from __future__ import annotations

import logging

import httpx

from athena.context import get_request_id
from athena.providers.exceptions import (
    ProviderAuthError,
    ProviderConnectionError,
    ProviderNotFoundError,
    ProviderParseError,
    ProviderRateLimitError,
    ProviderServerError,
)
from athena.providers.rate_limiter import RateLimiter
from athena.providers.retry import RetryPolicy

logger = logging.getLogger(__name__)


class ProviderClient:
    """Async HTTP client with built-in retry, rate limiting, and logging.

    Args:
        base_url:     Base URL for all requests (e.g. ``https://api.example.com/v4``).
        headers:      Default headers to include in every request
                      (authentication, content-type, etc.).
        timeout:      ``httpx.Timeout`` configuration.
        retry_policy: Retry behaviour (attempts, backoff, retryable exceptions).
        rate_limiter: Minimum-interval rate limiter.
        provider_name: Human-readable provider name for log records.
    """

    def __init__(
        self,
        base_url: str,
        headers: dict[str, str],
        timeout: httpx.Timeout,
        retry_policy: RetryPolicy,
        rate_limiter: RateLimiter,
        provider_name: str = "unknown",
    ) -> None:
        self._provider = provider_name
        self._retry_policy = retry_policy
        self._rate_limiter = rate_limiter
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers=headers,
            timeout=timeout,
        )

    # ── Public interface ──────────────────────────────────────────────────────

    async def get(
        self,
        path: str,
        *,
        params: dict | None = None,
    ) -> dict:
        """Execute a GET request with retry and rate limiting.

        Args:
            path:   URL path relative to ``base_url``.
            params: Query parameters (optional).

        Returns:
            Parsed JSON response body as a dict.

        Raises:
            ProviderConnectionError: Timeout or network failure (retried).
            ProviderRateLimitError:  HTTP 429 (retried with backoff).
            ProviderServerError:     HTTP 5xx (retried).
            ProviderAuthError:       HTTP 401/403 (not retried).
            ProviderNotFoundError:   HTTP 404 (not retried).
            ProviderParseError:      Response body is not valid JSON.
        """
        attempt = 0
        last_exc: Exception | None = None

        while True:
            attempt += 1
            await self._rate_limiter.acquire()

            logger.debug(
                "provider_request",
                extra={
                    "provider": self._provider,
                    "path": path,
                    "attempt": attempt,
                    "request_id": get_request_id(),
                },
            )

            try:
                response = await self._client.get(path, params=params)
                data = self._parse_and_raise(response)

                logger.debug(
                    "provider_response",
                    extra={
                        "provider": self._provider,
                        "path": path,
                        "status": response.status_code,
                        "attempt": attempt,
                    },
                )
                return data

            except (ProviderAuthError, ProviderNotFoundError, ProviderParseError):
                # Non-retryable — propagate immediately
                raise

            except Exception as exc:
                last_exc = exc
                if not self._retry_policy.should_retry(exc, attempt):
                    raise

                import asyncio
                wait = self._retry_policy.wait_for_rate_limit(exc, attempt)
                logger.warning(
                    "provider_retry",
                    extra={
                        "provider": self._provider,
                        "path": path,
                        "attempt": attempt,
                        "wait_s": round(wait, 2),
                        "error": type(exc).__name__,
                    },
                )
                await asyncio.sleep(wait)

    async def aclose(self) -> None:
        """Close the underlying HTTP client and release connections."""
        await self._client.aclose()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _parse_and_raise(self, response: httpx.Response) -> dict:
        """Convert HTTP status codes to typed exceptions; parse body."""
        status = response.status_code

        if status == 401 or status == 403:
            raise ProviderAuthError(
                f"Authentication failed (HTTP {status})",
                provider=self._provider,
            )

        if status == 404:
            raise ProviderNotFoundError(
                f"Resource not found (HTTP 404)",
                provider=self._provider,
            )

        if status == 429:
            retry_after: float | None = None
            raw = response.headers.get("retry-after")
            if raw and raw.isdigit():
                retry_after = float(raw)
            raise ProviderRateLimitError(
                "Rate limit exceeded (HTTP 429)",
                provider=self._provider,
                retry_after=retry_after,
            )

        if status >= 500:
            raise ProviderServerError(
                f"Server error (HTTP {status})",
                provider=self._provider,
                status_code=status,
            )

        if status >= 400:
            raise ProviderServerError(
                f"Unexpected client error (HTTP {status})",
                provider=self._provider,
                status_code=status,
            )

        try:
            return response.json()
        except Exception as exc:
            raise ProviderParseError(
                f"Failed to parse JSON response: {exc}",
                provider=self._provider,
            ) from exc

    # ── Context manager support ───────────────────────────────────────────────

    async def __aenter__(self) -> "ProviderClient":
        return self

    async def __aexit__(self, *args) -> None:
        await self.aclose()
