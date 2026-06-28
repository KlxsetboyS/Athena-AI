"""Unit tests for athena.logging_config.

Tests verify that configure_logging() executes without errors for all
supported formats and levels. We do not assert on the exact log output
format since that is structlog's responsibility and would make tests brittle.
"""
from __future__ import annotations

import logging



class TestConfigureLogging:
    def test_text_format_does_not_raise(self):
        from athena.logging_config import configure_logging
        configure_logging(level="INFO", fmt="text")

    def test_json_format_does_not_raise(self):
        from athena.logging_config import configure_logging
        configure_logging(level="INFO", fmt="json")

    def test_debug_level_applied(self):
        from athena.logging_config import configure_logging
        configure_logging(level="DEBUG", fmt="text")
        assert logging.getLogger().level == logging.DEBUG

    def test_warning_level_applied(self):
        from athena.logging_config import configure_logging
        configure_logging(level="WARNING", fmt="text")
        assert logging.getLogger().level == logging.WARNING

    def test_idempotent_reconfiguration(self):
        """Calling configure_logging twice must not raise."""
        from athena.logging_config import configure_logging
        configure_logging(level="INFO", fmt="text")
        configure_logging(level="DEBUG", fmt="json")
