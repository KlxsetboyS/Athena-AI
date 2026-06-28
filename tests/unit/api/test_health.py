"""Unit tests for /health (liveness) and /health/ready (readiness) endpoints.

``/health`` has no dependencies — always 200 while the process is alive.

``/health/ready`` reads ``app.state.db_engine`` set by the lifespan.
Tests inject a mock engine directly onto ``app.state`` to simulate both
the healthy and degraded cases without a real database connection.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from athena.api import create_app


@pytest.fixture
def app():
    return create_app(use_lifespan=False)


@pytest.fixture
async def client(app):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c, app


class TestLivenessEndpoint:
    async def test_health_returns_200(self, client):
        c, _ = client
        resp = await c.get("/health")
        assert resp.status_code == 200

    async def test_health_returns_ok_status(self, client):
        c, _ = client
        body = (await c.get("/health")).json()
        assert body["status"] == "ok"
        assert body["service"] == "athena-ai"

    async def test_health_always_200_even_without_lifespan(self, client):
        """Liveness probe must not depend on DB state."""
        c, _ = client
        # No app.state.db_engine set — should still be 200
        resp = await c.get("/health")
        assert resp.status_code == 200


class TestReadinessEndpoint:
    async def test_ready_returns_skipped_without_lifespan(self, client):
        """When lifespan has not run, /health/ready returns 200 with 'skipped'."""
        c, _ = client
        resp = await c.get("/health/ready")
        assert resp.status_code == 200
        body = resp.json()
        assert body["database"] == "skipped"

    async def test_ready_returns_200_when_db_ok(self, client):
        c, app = client
        mock_engine = MagicMock()
        app.state.db_engine = mock_engine

        with patch("athena.api.routers.health.async_ping", new_callable=AsyncMock) as mock_ping:
            mock_ping.return_value = True
            resp = await c.get("/health/ready")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ready"
        assert body["database"] == "ok"
        assert "latency_ms" in body

    async def test_ready_returns_503_when_db_unreachable(self, client):
        c, app = client
        mock_engine = MagicMock()
        app.state.db_engine = mock_engine

        with patch("athena.api.routers.health.async_ping", new_callable=AsyncMock) as mock_ping:
            mock_ping.side_effect = ConnectionRefusedError("connection refused")
            resp = await c.get("/health/ready")

        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "degraded"
        assert body["database"] == "error"
        assert "detail" in body

    async def test_ready_latency_field_present_on_success(self, client):
        c, app = client
        app.state.db_engine = MagicMock()

        with patch("athena.api.routers.health.async_ping", new_callable=AsyncMock):
            resp = await c.get("/health/ready")

        body = resp.json()
        assert isinstance(body.get("latency_ms"), float)

    async def test_ready_latency_field_present_on_failure(self, client):
        c, app = client
        app.state.db_engine = MagicMock()

        with patch("athena.api.routers.health.async_ping", new_callable=AsyncMock) as p:
            p.side_effect = Exception("timeout")
            resp = await c.get("/health/ready")

        body = resp.json()
        assert "latency_ms" in body
