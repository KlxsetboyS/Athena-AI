"""Unit tests for RequestIDMiddleware.

Tests the middleware behaviour directly via the ASGI test client,
without invoking any service or database logic.
"""
from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from athena.api import create_app


@pytest.fixture
def app():
    """App without lifespan so tests don't need a DB connection."""
    return create_app(use_lifespan=False)


@pytest.fixture
async def client(app):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


class TestRequestIDMiddleware:
    async def test_response_contains_request_id_header(self, client):
        """Every response must include X-Request-ID."""
        resp = await client.get("/health")
        assert "x-request-id" in resp.headers

    async def test_client_provided_id_is_echoed(self, client):
        """When the client sends X-Request-ID, it must be echoed back."""
        custom_id = "my-correlation-id-123"
        resp = await client.get("/health", headers={"X-Request-ID": custom_id})
        assert resp.headers["x-request-id"] == custom_id

    async def test_generated_id_is_valid_uuid(self, client):
        """When no ID is provided, the generated ID must be a valid UUID4."""
        resp = await client.get("/health")
        generated = resp.headers["x-request-id"]
        # Should not raise — valid UUID
        parsed = uuid.UUID(generated)
        assert parsed.version == 4

    async def test_different_requests_get_different_ids(self, client):
        """Each request without an explicit ID gets a unique correlation ID."""
        resp1 = await client.get("/health")
        resp2 = await client.get("/health")
        assert resp1.headers["x-request-id"] != resp2.headers["x-request-id"]

    async def test_custom_header_name(self, app):
        """Middleware respects the header_name configured in Settings."""
        # The default app uses X-Request-ID from Settings
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            resp = await c.get("/health", headers={"X-Request-ID": "test-123"})
        assert resp.headers.get("x-request-id") == "test-123"
