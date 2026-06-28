"""Tests for athena.context — ContextVar for request_id."""
from __future__ import annotations

import pytest

from athena.context import get_request_id, reset_request_id, set_request_id


class TestContext:
    def test_default_is_none(self):
        assert get_request_id() is None

    def test_set_and_get(self):
        token = set_request_id("test-id-123")
        try:
            assert get_request_id() == "test-id-123"
        finally:
            reset_request_id(token)

    def test_reset_restores_previous_value(self):
        assert get_request_id() is None
        token = set_request_id("abc")
        reset_request_id(token)
        assert get_request_id() is None

    def test_nested_set_and_reset(self):
        token1 = set_request_id("outer")
        token2 = set_request_id("inner")
        assert get_request_id() == "inner"
        reset_request_id(token2)
        assert get_request_id() == "outer"
        reset_request_id(token1)
        assert get_request_id() is None
