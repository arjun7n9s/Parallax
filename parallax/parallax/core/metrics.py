"""Prometheus metrics for PARALLAX.

Metrics that drive decisions, not vanity counters: per-role LLM latency and
token volume (the cost story), final-verdict distribution, and stage failures
broken out by error class (ties to the typed error hierarchy). The API exposes
these at /metrics, which the bundled Prometheus config already scrapes.

All recording goes through the helpers below, which are safe no-ops if
prometheus_client is unavailable, so callers never need to guard.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        Counter,
        Histogram,
        generate_latest,
    )

    _ENABLED = True
except Exception:  # pragma: no cover - prometheus_client is a declared dep
    _ENABLED = False

if _ENABLED:
    LLM_CALL_DURATION = Histogram(
        "parallax_llm_call_duration_seconds",
        "Wall-clock duration of a single LLM call",
        ["role", "provider"],
    )
    LLM_TOKENS = Counter(
        "parallax_llm_tokens_total",
        "LLM tokens consumed",
        ["role", "direction"],  # direction = input | output
    )
    ANALYSIS_VERDICT = Counter(
        "parallax_analysis_verdict_total",
        "Final analysis verdicts",
        ["verdict"],
    )
    STAGE_FAILURE = Counter(
        "parallax_stage_failure_total",
        "Pipeline stage failures by error class",
        ["stage", "error_class"],
    )


def record_llm_call(
    role: str, provider: str, duration_s: float, tokens_in: int = 0, tokens_out: int = 0
) -> None:
    if not _ENABLED:
        return
    try:
        LLM_CALL_DURATION.labels(role=role, provider=provider).observe(duration_s)
        if tokens_in:
            LLM_TOKENS.labels(role=role, direction="input").inc(tokens_in)
        if tokens_out:
            LLM_TOKENS.labels(role=role, direction="output").inc(tokens_out)
    except Exception as exc:  # noqa: BLE001 - metrics must never break the pipeline
        logger.debug("record_llm_call failed: %s", exc)


def record_verdict(verdict: str) -> None:
    if not _ENABLED:
        return
    try:
        ANALYSIS_VERDICT.labels(verdict=str(verdict)).inc()
    except Exception as exc:  # noqa: BLE001
        logger.debug("record_verdict failed: %s", exc)


def record_stage_failure(stage: str, exc: BaseException) -> None:
    if not _ENABLED:
        return
    try:
        STAGE_FAILURE.labels(stage=stage, error_class=type(exc).__name__).inc()
    except Exception as e:  # noqa: BLE001
        logger.debug("record_stage_failure failed: %s", e)


def metrics_text() -> tuple[bytes, str]:
    """Return (body, content_type) for the /metrics endpoint."""
    if not _ENABLED:
        return b"", "text/plain"
    return generate_latest(), CONTENT_TYPE_LATEST
