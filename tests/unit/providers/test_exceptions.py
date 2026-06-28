"""Tests for the provider exception hierarchy."""
from __future__ import annotations

import pytest

from athena.providers.exceptions import (
    ProviderAuthError,
    ProviderConnectionError,
    ProviderDataError,
    ProviderError,
    ProviderNetworkError,
    ProviderNotFoundError,
    ProviderParseError,
    ProviderRateLimitError,
    ProviderServerError,
)


class TestExceptionHierarchy:
    def test_connection_error_is_network_error(self):
        assert issubclass(ProviderConnectionError, ProviderNetworkError)

    def test_rate_limit_error_is_network_error(self):
        assert issubclass(ProviderRateLimitError, ProviderNetworkError)

    def test_server_error_is_network_error(self):
        assert issubclass(ProviderServerError, ProviderNetworkError)

    def test_network_error_is_provider_error(self):
        assert issubclass(ProviderNetworkError, ProviderError)

    def test_auth_error_is_provider_error(self):
        assert issubclass(ProviderAuthError, ProviderError)

    def test_parse_error_is_data_error(self):
        assert issubclass(ProviderParseError, ProviderDataError)

    def test_not_found_error_is_data_error(self):
        assert issubclass(ProviderNotFoundError, ProviderDataError)

    def test_data_error_is_provider_error(self):
        assert issubclass(ProviderDataError, ProviderError)

    def test_auth_error_is_not_network_error(self):
        assert not issubclass(ProviderAuthError, ProviderNetworkError)

    def test_parse_error_is_not_network_error(self):
        assert not issubclass(ProviderParseError, ProviderNetworkError)


class TestExceptionMessages:
    def test_provider_name_in_message(self):
        exc = ProviderConnectionError("timeout", provider="football-data")
        assert "football-data" in str(exc)
        assert "timeout" in str(exc)

    def test_rate_limit_stores_retry_after(self):
        exc = ProviderRateLimitError("429", provider="odds-api", retry_after=30.0)
        assert exc.retry_after == 30.0
        assert exc.provider == "odds-api"

    def test_server_error_stores_status_code(self):
        exc = ProviderServerError("503", provider="football-data", status_code=503)
        assert exc.status_code == 503

    def test_catch_as_network_error(self):
        exc = ProviderServerError("503", status_code=503)
        assert isinstance(exc, ProviderNetworkError)
        assert isinstance(exc, ProviderError)
