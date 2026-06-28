"""Provider exception hierarchy for Athena AI.

Two branches keep semantics clear:

ProviderNetworkError
    Problems at the transport layer — timeout, DNS failure, rate limit,
    server error.  All of these are candidates for retry.

ProviderAuthError
    Authentication / authorisation failure.  Not retryable — the API key
    is wrong or expired and retrying immediately will not help.

ProviderDataError
    Problems with the content returned by the provider — JSON that cannot
    be parsed, or a resource that the provider says does not exist.
    Retrying will not help.

Usage in ProviderClient
-----------------------
``ProviderClient`` converts HTTP status codes into these exceptions *before*
passing control to ``RetryPolicy``.  ``RetryPolicy`` therefore never needs
to know about HTTP — it works exclusively with exception types.

    except httpx.TimeoutException:
        raise ProviderConnectionError(...)
    if response.status_code == 429:
        raise ProviderRateLimitError(...)
    if response.status_code in (500, 502, 503, 504):
        raise ProviderServerError(...)
    if response.status_code in (401, 403):
        raise ProviderAuthError(...)
    if response.status_code == 404:
        raise ProviderNotFoundError(...)
"""
from __future__ import annotations


class ProviderError(Exception):
    """Base class for all provider-layer errors.

    Attributes:
        provider: Name of the provider that raised the error.
        message:  Human-readable description of the failure.
    """

    def __init__(self, message: str, *, provider: str = "unknown") -> None:
        self.provider = provider
        self.message = message
        super().__init__(f"[{provider}] {message}")


# ── Network / transport branch ────────────────────────────────────────────────

class ProviderNetworkError(ProviderError):
    """Base class for transport-layer errors that may be retried."""


class ProviderConnectionError(ProviderNetworkError):
    """Timeout, DNS failure, TLS error, or connection refused.

    Corresponds to ``httpx.TimeoutException`` and ``httpx.ConnectError``.
    """


class ProviderRateLimitError(ProviderNetworkError):
    """The provider returned HTTP 429 Too Many Requests.

    Retry after the interval indicated by ``retry_after`` (seconds), or use
    exponential backoff if the provider does not send a ``Retry-After`` header.

    Attributes:
        retry_after: Suggested wait time in seconds, or ``None`` if unknown.
    """

    def __init__(
        self,
        message: str,
        *,
        provider: str = "unknown",
        retry_after: float | None = None,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(message, provider=provider)


class ProviderServerError(ProviderNetworkError):
    """The provider returned HTTP 5xx.

    Attributes:
        status_code: The HTTP status code received (500, 502, 503, 504, …).
    """

    def __init__(
        self,
        message: str,
        *,
        provider: str = "unknown",
        status_code: int | None = None,
    ) -> None:
        self.status_code = status_code
        super().__init__(message, provider=provider)


# ── Auth branch ───────────────────────────────────────────────────────────────

class ProviderAuthError(ProviderError):
    """HTTP 401 or 403 — API key is missing, invalid, or expired.

    Not retryable.  The operator must update the API key in Settings.
    """


# ── Data / content branch ─────────────────────────────────────────────────────

class ProviderDataError(ProviderError):
    """Base class for errors related to the content returned by the provider."""


class ProviderParseError(ProviderDataError):
    """The provider returned a response that could not be parsed.

    Either the JSON is malformed or the mapper encountered an unexpected
    schema (missing required field, wrong type, etc.).
    """


class ProviderNotFoundError(ProviderDataError):
    """HTTP 404 — the requested resource does not exist at the provider.

    Not retryable.  The caller should log and skip this resource.
    """
