"""
Structured logging configuration for PARALLAX using structlog.

Renders human-readable colored output for an interactive terminal and
machine-parseable JSON everywhere else (containers, CI, production), so the
same code ships to Loki/ELK without changes. ``settings.LOG_FORMAT`` ("auto" |
"json" | "console") overrides the TTY heuristic.

Per-submission correlation: bind a submission id once with ``bind_log_context``
and every subsequent log line in that task — across all modules — carries it,
so a single analysis can be traced end to end without threading ids through
function signatures.

Usage:
    from parallax.core.logging import setup_logging, bind_log_context
    setup_logging("DEBUG")
    bind_log_context(submission_id=sid, stage="static")
"""

import logging
import sys
from typing import Any

import structlog


def _use_json(log_format: str) -> bool:
    fmt = (log_format or "auto").lower()
    if fmt == "json":
        return True
    if fmt == "console":
        return False
    # auto: JSON unless attached to an interactive terminal.
    return not sys.stdout.isatty()


_SHARED_PROCESSORS: list[Any] = [
    # Merge any context bound via bind_log_context into every event.
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
]


def _build_formatter(log_format: str) -> "structlog.stdlib.ProcessorFormatter":
    renderer: Any = (
        structlog.processors.JSONRenderer()
        if _use_json(log_format)
        else structlog.dev.ConsoleRenderer(colors=True)
    )
    return structlog.stdlib.ProcessorFormatter(  # type: ignore
        foreign_pre_chain=_SHARED_PROCESSORS,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )


def setup_logging(log_level: str = "INFO", log_format: str = "auto") -> None:
    """
    Configure structured logging via structlog.

    Args:
        log_level: One of DEBUG, INFO, WARNING, ERROR, CRITICAL.
                   Defaults to INFO if an invalid value is passed.
        log_format: "auto" (default), "json", or "console".
    """
    structlog.configure(  # type: ignore
        processors=_SHARED_PROCESSORS
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = _build_formatter(log_format)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    if not root_logger.handlers:
        root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))


def bind_log_context(**kwargs: Any) -> None:
    """Bind key/value pairs to the current context so they appear on every
    subsequent log line in this task/request (uses contextvars, so it is safe
    across async boundaries and isolated per task)."""
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_log_context() -> None:
    """Drop all bound context — call at the end of a task to avoid leaking ids
    into the next unit of work scheduled on the same worker."""
    structlog.contextvars.clear_contextvars()
