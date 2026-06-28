"""Tests for RetryPolicy — pure calculations, no I/O."""
from __future__ import annotations

import pytest

from athena.providers.exceptions import (
    ProviderAuthError,
    ProviderConnectionError,
    ProviderParseError,
    ProviderRateLimitError,
    ProviderServerError,
)
from athena.providers.retry import RetryPolicy


class TestShouldRetry:
    def test_retryable_exception_within_attempts(self):
        policy = RetryPolicy(max_attempts=3)
        assert policy.should_retry(ProviderConnectionError("timeout"), attempt=1)

    def test_retryable_exception_at_last_attempt(self):
        policy = RetryPolicy(max_attempts=3)
        # attempt=3 is the last allowed — no more retries
        assert not policy.should_retry(ProviderConnectionError("timeout"), attempt=3)

    def test_non_retryable_exception(self):
        policy = RetryPolicy(max_attempts=3)
        assert not policy.should_retry(ProviderAuthError("401"), attempt=1)

    def test_parse_error_not_retried(self):
        policy = RetryPolicy(max_attempts=3)
        assert not policy.should_retry(ProviderParseError("bad json"), attempt=1)

    def test_server_error_is_retried(self):
        policy = RetryPolicy(max_attempts=3)
        assert policy.should_retry(ProviderServerError("503", status_code=503), attempt=1)

    def test_rate_limit_is_retried(self):
        policy = RetryPolicy(max_attempts=3)
        assert policy.should_retry(ProviderRateLimitError("429"), attempt=1)

    def test_max_attempts_one_never_retries(self):
        policy = RetryPolicy(max_attempts=1)
        assert not policy.should_retry(ProviderConnectionError("timeout"), attempt=1)


class TestWaitSeconds:
    def test_first_attempt_wait(self):
        policy = RetryPolicy(max_attempts=3, backoff_base=1.0, jitter=False)
        assert policy.wait_seconds(attempt=1) == pytest.approx(1.0)

    def test_second_attempt_doubles(self):
        policy = RetryPolicy(max_attempts=3, backoff_base=1.0, jitter=False)
        assert policy.wait_seconds(attempt=2) == pytest.approx(2.0)

    def test_third_attempt_doubles_again(self):
        policy = RetryPolicy(max_attempts=3, backoff_base=1.0, jitter=False)
        assert policy.wait_seconds(attempt=3) == pytest.approx(4.0)

    def test_wait_capped_at_backoff_max(self):
        policy = RetryPolicy(backoff_base=10.0, backoff_max=15.0, jitter=False)
        # 10 * 2^3 = 80, capped at 15
        assert policy.wait_seconds(attempt=4) == pytest.approx(15.0)

    def test_jitter_within_bounds(self):
        policy = RetryPolicy(max_attempts=3, backoff_base=1.0, jitter=True)
        for _ in range(50):
            w = policy.wait_seconds(attempt=1)
            assert 0.5 <= w <= 1.5

    def test_custom_base(self):
        policy = RetryPolicy(backoff_base=2.0, jitter=False)
        assert policy.wait_seconds(attempt=1) == pytest.approx(2.0)
        assert policy.wait_seconds(attempt=2) == pytest.approx(4.0)


class TestWaitForRateLimit:
    def test_honours_retry_after_when_set(self):
        policy = RetryPolicy(jitter=False)
        exc = ProviderRateLimitError("429", retry_after=30.0)
        assert policy.wait_for_rate_limit(exc, attempt=1) == pytest.approx(30.0)

    def test_falls_back_to_backoff_when_no_retry_after(self):
        policy = RetryPolicy(backoff_base=1.0, jitter=False)
        exc = ProviderRateLimitError("429", retry_after=None)
        # Falls back to normal backoff: 1.0 * 2^0 = 1.0
        assert policy.wait_for_rate_limit(exc, attempt=1) == pytest.approx(1.0)

    def test_non_rate_limit_uses_backoff(self):
        policy = RetryPolicy(backoff_base=1.0, jitter=False)
        exc = ProviderConnectionError("timeout")
        assert policy.wait_for_rate_limit(exc, attempt=1) == pytest.approx(1.0)
