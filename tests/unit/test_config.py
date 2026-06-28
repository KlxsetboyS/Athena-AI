"""Unit tests for athena.config.Settings.

All tests use monkeypatch to set environment variables and call
``get_settings.cache_clear()`` to ensure a fresh Settings instance.
No I/O, no database, no FastAPI.
"""
from __future__ import annotations

import pytest

from athena.config import Settings, get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Ensure each test gets a fresh Settings instance."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestSettingsDefaults:
    def test_database_url_default(self):
        s = Settings()
        assert s.database_url == "sqlite+aiosqlite:///./athena.db"

    def test_database_echo_default_false(self):
        s = Settings()
        assert s.database_echo is False

    def test_database_pool_size_default(self):
        s = Settings()
        assert s.database_pool_size == 5

    def test_log_level_default(self):
        s = Settings()
        assert s.log_level == "INFO"

    def test_log_format_default(self):
        s = Settings()
        assert s.log_format == "text"

    def test_app_env_default(self):
        s = Settings()
        assert s.app_env == "development"

    def test_request_id_header_default(self):
        s = Settings()
        assert s.request_id_header == "X-Request-ID"


class TestSettingsFromEnvironment:
    def test_database_url_from_env(self, monkeypatch):
        monkeypatch.setenv(
            "DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db"
        )
        s = Settings()
        assert s.database_url == "postgresql+asyncpg://user:pass@localhost/db"

    def test_database_echo_from_env(self, monkeypatch):
        monkeypatch.setenv("DATABASE_ECHO", "true")
        s = Settings()
        assert s.database_echo is True

    def test_log_level_from_env(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        s = Settings()
        assert s.log_level == "DEBUG"

    def test_log_format_json_from_env(self, monkeypatch):
        monkeypatch.setenv("LOG_FORMAT", "json")
        s = Settings()
        assert s.log_format == "json"

    def test_app_env_production(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "production")
        s = Settings()
        assert s.app_env == "production"

    def test_request_id_header_custom(self, monkeypatch):
        monkeypatch.setenv("REQUEST_ID_HEADER", "X-Correlation-ID")
        s = Settings()
        assert s.request_id_header == "X-Correlation-ID"

    def test_case_insensitive_env(self, monkeypatch):
        monkeypatch.setenv("log_level", "WARNING")
        s = Settings()
        assert s.log_level == "WARNING"


class TestSettingsValidation:
    def test_sync_postgres_url_rejected(self):
        with pytest.raises(Exception):
            Settings(database_url="postgresql://user:pass@host/db")

    def test_sync_sqlite_url_rejected(self):
        with pytest.raises(Exception):
            Settings(database_url="sqlite:///./athena.db")

    def test_async_sqlite_url_accepted(self):
        s = Settings(database_url="sqlite+aiosqlite:///./athena.db")
        assert "aiosqlite" in s.database_url

    def test_async_postgres_url_accepted(self):
        s = Settings(database_url="postgresql+asyncpg://u:p@host/db")
        assert "asyncpg" in s.database_url

    def test_pool_size_zero_rejected(self):
        with pytest.raises(Exception):
            Settings(database_pool_size=0)

    def test_pool_size_negative_rejected(self):
        with pytest.raises(Exception):
            Settings(database_pool_size=-1)

    def test_invalid_log_level_rejected(self):
        with pytest.raises(Exception):
            Settings(log_level="VERBOSE")

    def test_invalid_log_format_rejected(self):
        with pytest.raises(Exception):
            Settings(log_format="yaml")

    def test_invalid_app_env_rejected(self):
        with pytest.raises(Exception):
            Settings(app_env="staging")


class TestGetSettingsCache:
    def test_returns_same_instance(self):
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_cache_clear_returns_new_instance(self, monkeypatch):
        s1 = get_settings()
        get_settings.cache_clear()
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        s2 = get_settings()
        # They are different instances after clearing
        assert s1 is not s2
        assert s2.log_level == "DEBUG"
