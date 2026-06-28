"""Retry policy for provider HTTP calls.

Design
------
``RetryPolicy`` is a pure data object that calculates wait times.
It has no I/O — it does not call ``asyncio.sleep``.

``ProviderClient`` is responsible for:
1. Converting HTTP status codes to exceptions.
2. Calling ``policy.should_retry(exc)`` to decide whether to retry.
3. Calling ``policy.wait_seconds(attempt)`` to get the delay.
4. Executing ``await asyncio.sleep(delay)``.

This separation makes both classes independently testable:
- RetryPolicy tests verify the maths without any async setup.
- ProviderClient tests mock ``asyncio.sleep`` without caring about backoff.

Configuration
-------------
All parameters come from ``athena.config.Settings`` and are injected
at construction time. ``ProviderClient`` builds the policy from settings.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from athena.providers.exceptions import (
    ProviderConnectionError,
    ProviderNetworkError,
    ProviderRateLimitError,
    ProviderServerError,
)

# Default set of retryable exception types.
# ProviderAuthError and ProviderDataError are NOT retryable.
DEFAULT_RETRYABLE: tuple[type[Exception], ...] = (
    ProviderConnectionError,
    ProviderRateLimitError,
    ProviderServerError,
)


@dataclass(frozen=True)
class RetryPolicy:
    """Immutable retry configuration for a provider client.

    Attributes:
        max_attempts:        Total number of attempts (1 = no retries).
        backoff_base:        Base wait time in seconds for exponential backoff.
        backoff_max:         Maximum wait time cap in seconds.
        jitter:              When True, randomises wait by ±50 % to avoid
                             thundering-herd on shared infrastructure.
        retryable_exceptions: Tuple of exception types that trigger a retry.
    """

    max_attempts: int = 3
    backoff_base: float = 1.0
    backoff_max: float = 60.0
    jitter: bool = True
    retryable_exceptions: tuple[type[Exception], ...] = field(
        default_factory=lambda: DEFAULT_RETRYABLE
    )

    def should_retry(self, exc: Exception, attempt: int) -> bool:
        """Return True if *exc* warrants a retry on *attempt*.

        Args:
            exc:     The exception raised by the last attempt.
            attempt: 1-based attempt number that just failed.
        """
        if attempt >= self.max_attempts:
            return False
        return isinstance(exc, self.retryable_exceptions)

    def wait_seconds(self, attempt: int) -> float:
        """Return the number of seconds to wait before the next attempt.

        Uses exponential backoff with optional jitter.

        Args:
            attempt: 1-based attempt number that just failed (so the next
                     attempt will be ``attempt + 1``).
        """
        # Exponential: 1s, 2s, 4s, 8s … capped at backoff_max
        delay = min(self.backoff_base * (2 ** (attempt - 1)), self.backoff_max)
        if self.jitter:
            delay *= random.uniform(0.5, 1.5)
        return delay

    # ── Special handling for rate-limit errors ────────────────────────────────

    def wait_for_rate_limit(self, exc: Exception, attempt: int) -> float:
        """Return wait time, honouring ``retry_after`` for rate-limit errors."""
        if isinstance(exc, ProviderRateLimitError) and exc.retry_after is not None:
            return exc.retry_after
        return self.wait_seconds(attempt)
