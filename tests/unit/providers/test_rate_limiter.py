"""Tests for RateLimiter — asyncio.sleep is mocked to avoid real delays."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch


from athena.providers.rate_limiter import RateLimiter


class TestRateLimiterDisabled:
    async def test_zero_interval_does_not_sleep(self):
        limiter = RateLimiter(min_interval_seconds=0.0)
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await limiter.acquire()
            mock_sleep.assert_not_awaited()

    async def test_negative_interval_does_not_sleep(self):
        limiter = RateLimiter(min_interval_seconds=-1.0)
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await limiter.acquire()
            mock_sleep.assert_not_awaited()


class TestRateLimiterEnabled:
    async def test_first_call_does_not_sleep(self):
        """First call always goes through immediately (no previous timestamp)."""
        limiter = RateLimiter(min_interval_seconds=6.0)
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await limiter.acquire()
            mock_sleep.assert_not_awaited()

    async def test_acquire_returns_without_error(self):
        limiter = RateLimiter(min_interval_seconds=0.01)
        # Should not raise even with a very short interval
        await limiter.acquire()

    async def test_semaphore_present(self):
        """RateLimiter must have a Semaphore for coroutine safety."""
        limiter = RateLimiter(min_interval_seconds=1.0)
        import asyncio
        assert isinstance(limiter._semaphore, asyncio.Semaphore)

    async def test_min_interval_stored(self):
        limiter = RateLimiter(min_interval_seconds=6.0)
        assert limiter._min_interval == 6.0
