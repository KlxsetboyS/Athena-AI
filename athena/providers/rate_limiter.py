"""Rate limiter for outgoing provider HTTP requests.

Design
------
A simple **minimum-interval** limiter (leaky bucket) backed by
``asyncio.Semaphore(1)``.

Why not a token bucket?
    Token buckets are correct for bursty workloads with many concurrent
    callers.  Provider ingestión in Sprint 2.2 is sequential: one coroutine
    drains the queue.  A minimum-interval approach is exact and has no
    thundering-herd issue because the Semaphore(1) serialises callers.

Concurrency guarantee
    ``asyncio.Semaphore(1)`` ensures only one coroutine executes the
    critical section at a time.  The ``asyncio.sleep`` inside releases the
    event loop so other tasks can run during the wait.

Usage::

    limiter = RateLimiter(min_interval_seconds=6.0)  # 10 req/min
    await limiter.acquire()
    response = await httpx_client.get(...)
"""
from __future__ import annotations

import asyncio
import time


class RateLimiter:
    """Enforce a minimum interval between consecutive requests.

    Args:
        min_interval_seconds: Minimum time in seconds between calls to
                              ``acquire()``.  Set to 0.0 to disable limiting.
    """

    def __init__(self, min_interval_seconds: float) -> None:
        self._min_interval = min_interval_seconds
        self._last_call: float = 0.0
        self._semaphore = asyncio.Semaphore(1)

    async def acquire(self) -> None:
        """Wait until the minimum interval has elapsed, then return.

        Blocks (yields to event loop) if the previous request was too recent.
        Thread/coroutine-safe via Semaphore(1).
        """
        async with self._semaphore:
            if self._min_interval <= 0.0:
                return
            now = time.monotonic()
            elapsed = now - self._last_call
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            self._last_call = time.monotonic()
