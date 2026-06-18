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

_PREMIUM_ROLES = {"re_workbench", "code_interpreter", "synthesis"}
_LONG_CONTEXT_ROLES = {"behavior_analyst", "evidence_validator", "dynamic_explorer", "visual"}

# Approximate public USD-per-million-token bands. These are intentionally
# conservative planning numbers for spend alerts, not accounting invoices.
_USD_PER_MILLION = {
    "economy": {"input": 0.15, "output": 0.60},
    "long_context": {"input": 0.30, "output": 2.50},
    "premium": {"input": 3.00, "output": 15.00},
}

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        Counter,
        Gauge,
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
    LLM_COST = Counter(
        "parallax_llm_cost_usd_total",
        "Estimated LLM spend in USD",
        ["role", "provider"],
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
    ORPHAN_REAPED = Counter(
        "parallax_orphan_reaped_total",
        "Orphaned analyses re-queued by the reaper, by resumed stage",
        ["stage"],
    )
    TAIG_NODES = Gauge(
        "parallax_taig_nodes",
        "TAIG graph node counts by label",
        ["label"],
    )
    TAIG_EDGES = Gauge(
        "parallax_taig_edges",
        "TAIG graph relationship counts by type",
        ["type"],
    )
    TAIG_HEALTH = Gauge(
        "parallax_taig_health",
        "TAIG graph health check counts",
        ["check"],
    )


def estimate_llm_cost_usd(role: str, provider: str, tokens_in: int, tokens_out: int) -> float:
    """Estimate LLM cost for alerting. Local Ollama inference is treated as
    zero marginal API spend; host compute is tracked separately by ops."""
    if provider == "ollama":
        return 0.0
    if role in _PREMIUM_ROLES:
        tier = "premium"
    elif role in _LONG_CONTEXT_ROLES:
        tier = "long_context"
    else:
        tier = "economy"
    prices = _USD_PER_MILLION[tier]
    return (tokens_in * prices["input"] + tokens_out * prices["output"]) / 1_000_000


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
        cost_usd = estimate_llm_cost_usd(role, provider, tokens_in, tokens_out)
        if cost_usd:
            LLM_COST.labels(role=role, provider=provider).inc(cost_usd)
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


def record_orphan_reaped(stage: str) -> None:
    if not _ENABLED:
        return
    try:
        ORPHAN_REAPED.labels(stage=stage).inc()
    except Exception as exc:  # noqa: BLE001
        logger.debug("record_orphan_reaped failed: %s", exc)


def record_graph_health(snapshot: dict) -> None:
    if not _ENABLED:
        return
    try:
        for label, count in snapshot.get("node_counts", {}).items():
            TAIG_NODES.labels(label=str(label)).set(float(count))
        for rel_type, count in snapshot.get("edge_counts", {}).items():
            TAIG_EDGES.labels(type=str(rel_type)).set(float(count))
        for check in ("orphan_apks", "orphan_iocs", "broken_relationships", "missing_key_nodes"):
            TAIG_HEALTH.labels(check=check).set(float(snapshot.get(check, 0)))
    except Exception as exc:  # noqa: BLE001
        logger.debug("record_graph_health failed: %s", exc)


def metrics_text() -> tuple[bytes, str]:
    """Return (body, content_type) for the /metrics endpoint."""
    if not _ENABLED:
        return b"", "text/plain"
    return generate_latest(), CONTENT_TYPE_LATEST
