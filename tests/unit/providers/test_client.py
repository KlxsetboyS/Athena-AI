"""Tests for ProviderClient using httpx.MockTransport.

No real HTTP calls are made.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from athena.providers.client import ProviderClient
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


def _make_client(transport: httpx.MockTransport) -> ProviderClient:
    """Build a ProviderClient with no retries and no rate limiting."""
    client = ProviderClient(
        base_url="https://api.test.com",
        headers={"X-Test": "1"},
        timeout=httpx.Timeout(5.0),
        retry_policy=RetryPolicy(max_attempts=1, jitter=False),
        rate_limiter=RateLimiter(min_interval_seconds=0.0),
        provider_name="test",
    )
    # Replace the internal httpx client with a mock transport
    client._client = httpx.AsyncClient(
        base_url="https://api.test.com",
        transport=transport,
    )
    return client


def _json_transport(data: dict | list, status_code: int = 200) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=status_code,
            json=data,
        )
    return httpx.MockTransport(handler)


def _status_transport(status_code: int) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=status_code, json={"error": "test"})
    return httpx.MockTransport(handler)


class TestSuccessfulRequest:
    async def test_returns_parsed_json(self):
        transport = _json_transport({"competitions": []})
        client = _make_client(transport)
        result = await client.get("/competitions")
        assert result == {"competitions": []}
        await client.aclose()

    async def test_passes_query_params(self):
        received_params = {}

        def handler(request: httpx.Request) -> httpx.Response:
            received_params.update(dict(request.url.params))
            return httpx.Response(200, json={"ok": True})

        client = _make_client(httpx.MockTransport(handler))
        await client.get("/test", params={"foo": "bar"})
        assert received_params.get("foo") == "bar"
        await client.aclose()


class TestHttpErrorMapping:
    async def test_401_raises_auth_error(self):
        client = _make_client(_status_transport(401))
        with pytest.raises(ProviderAuthError):
            await client.get("/test")
        await client.aclose()

    async def test_403_raises_auth_error(self):
        client = _make_client(_status_transport(403))
        with pytest.raises(ProviderAuthError):
            await client.get("/test")
        await client.aclose()

    async def test_404_raises_not_found(self):
        client = _make_client(_status_transport(404))
        with pytest.raises(ProviderNotFoundError):
            await client.get("/test")
        await client.aclose()

    async def test_429_raises_rate_limit(self):
        client = _make_client(_status_transport(429))
        with pytest.raises(ProviderRateLimitError):
            await client.get("/test")
        await client.aclose()

    async def test_503_raises_server_error(self):
        client = _make_client(_status_transport(503))
        with pytest.raises(ProviderServerError):
            await client.get("/test")
        await client.aclose()

    async def test_500_raises_server_error(self):
        client = _make_client(_status_transport(500))
        with pytest.raises(ProviderServerError):
            await client.get("/test")
        await client.aclose()


class TestRetryBehaviour:
    async def test_retries_on_server_error(self):
        """With max_attempts=3, a 503 is retried and succeeds on attempt 3."""
        call_count = [0]

        def handler(request: httpx.Request) -> httpx.Response:
            call_count[0] += 1
            if call_count[0] < 3:
                return httpx.Response(503, json={"error": "unavailable"})
            return httpx.Response(200, json={"ok": True})

        client = ProviderClient(
            base_url="https://api.test.com",
            headers={},
            timeout=httpx.Timeout(5.0),
            retry_policy=RetryPolicy(max_attempts=3, backoff_base=0.0, jitter=False),
            rate_limiter=RateLimiter(min_interval_seconds=0.0),
            provider_name="test",
        )
        client._client = httpx.AsyncClient(
            base_url="https://api.test.com",
            transport=httpx.MockTransport(handler),
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await client.get("/test")

        assert result == {"ok": True}
        assert call_count[0] == 3
        await client.aclose()

    async def test_no_retry_on_auth_error(self):
        """Auth errors are not retried even with max_attempts > 1."""
        call_count = [0]

        def handler(request: httpx.Request) -> httpx.Response:
            call_count[0] += 1
            return httpx.Response(401, json={"error": "unauthorized"})

        client = ProviderClient(
            base_url="https://api.test.com",
            headers={},
            timeout=httpx.Timeout(5.0),
            retry_policy=RetryPolicy(max_attempts=3),
            rate_limiter=RateLimiter(min_interval_seconds=0.0),
            provider_name="test",
        )
        client._client = httpx.AsyncClient(
            base_url="https://api.test.com",
            transport=httpx.MockTransport(handler),
        )

        with pytest.raises(ProviderAuthError):
            await client.get("/test")

        assert call_count[0] == 1  # no retries
        await client.aclose()


class TestParseError:
    async def test_invalid_json_raises_parse_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"not valid json", headers={"content-type": "text/plain"})

        client = _make_client(httpx.MockTransport(handler))
        with pytest.raises(ProviderParseError):
            await client.get("/test")
        await client.aclose()
