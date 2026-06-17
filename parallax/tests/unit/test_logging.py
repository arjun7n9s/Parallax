"""Tests for structured logging: format selection and per-task context binding."""

import json
import logging

import structlog

from parallax.core.logging import (
    _build_formatter,
    _use_json,
    bind_log_context,
    clear_log_context,
)


class TestFormatSelection:
    def test_json_when_explicit(self):
        assert _use_json("json") is True

    def test_console_when_explicit(self):
        assert _use_json("console") is False

    def test_auto_is_json_when_not_a_tty(self, monkeypatch):
        # Pytest captures stdout, so isatty() is False; auto must pick JSON.
        monkeypatch.setattr("sys.stdout.isatty", lambda: False, raising=False)
        assert _use_json("auto") is True


class TestContextBinding:
    def teardown_method(self):
        clear_log_context()

    def test_bound_context_appears_in_json_log(self):
        # Render a stdlib record through the production JSON formatter; the
        # foreign_pre_chain merges bound contextvars into the event.
        formatter = _build_formatter("json")
        bind_log_context(submission_id="sub-123", stage="static")
        rec = logging.LogRecord("parallax.test", logging.WARNING, __file__, 1, "hello", None, None)
        record = json.loads(formatter.format(rec))
        assert record["submission_id"] == "sub-123"
        assert record["stage"] == "static"
        assert record["event"] == "hello"
        assert record["level"] == "warning"

    def test_clear_drops_context(self):
        bind_log_context(submission_id="sub-xyz")
        clear_log_context()
        # No bound vars remain after clear.
        assert structlog.contextvars.get_contextvars() == {}
