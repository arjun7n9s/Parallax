"""Outbound webhook dispatch for analysis events.

HMAC-signed JSON payloads with bounded exponential-backoff retries. Webhook
targets are configured per deployment; when none are configured this is a no-op.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging

import httpx

from parallax.core.config import settings

logger = logging.getLogger(__name__)

EVENT_ANALYSIS_COMPLETED = "analysis.completed"
EVENT_VERDICT_CRITICAL = "verdict.critical"


def _targets() -> list[str]:
    raw = getattr(settings, "WEBHOOK_URLS", "") or ""
    return [u.strip() for u in raw.split(",") if u.strip()]


def _sign(body: bytes) -> str:
    secret = (getattr(settings, "WEBHOOK_SECRET", "") or "").encode()
    if not secret:
        return ""
    return hmac.new(secret, body, hashlib.sha256).hexdigest()


def _build_request(event_type: str, payload: dict) -> tuple[bytes, dict]:
    """Serialize + HMAC-sign one event into (body, headers)."""
    body = json.dumps({"event": event_type, "data": payload}).encode()
    headers = {"Content-Type": "application/json"}
    sig = _sign(body)
    if sig:
        headers["X-Parallax-Signature"] = f"sha256={sig}"
    else:
        logger.warning(
            "WEBHOOK_SECRET is not set — dispatching UNSIGNED webhooks. "
            "Receivers cannot verify authenticity; set WEBHOOK_SECRET and "
            "verify X-Parallax-Signature (hmac.compare_digest over the raw body)."
        )
    return body, headers


async def _post_with_retries(
    client: httpx.AsyncClient, url: str, body: bytes, headers: dict, max_retries: int
) -> bool:
    """POST one body to one URL with bounded exponential backoff. True on a 2xx."""
    for attempt in range(max_retries):
        try:
            resp = await client.post(url, content=body, headers=headers)
            if resp.status_code < 300:
                return True
            raise httpx.HTTPStatusError("bad status", request=resp.request, response=resp)
        except Exception as exc:  # noqa: BLE001
            backoff = 2**attempt
            logger.warning(
                "Webhook %s attempt %d failed: %s (retry in %ds)", url, attempt + 1, exc, backoff
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(backoff)
    return False


async def dispatch(event_type: str, payload: dict, max_retries: int = 4) -> dict:
    """Send an event to all deployment-configured webhook targets with retries."""
    targets = _targets()
    if not targets:
        logger.debug("No webhook targets configured; skipping %s", event_type)
        return {"delivered": 0, "targets": 0}

    body, headers = _build_request(event_type, payload)
    delivered = 0
    async with httpx.AsyncClient(timeout=15.0) as client:
        for url in targets:
            if await _post_with_retries(client, url, body, headers, max_retries):
                delivered += 1
    return {"delivered": delivered, "targets": len(targets)}


async def dispatch_to_url(url: str, event_type: str, payload: dict, max_retries: int = 4) -> dict:
    """Send one event to a single explicit subscriber URL — the per-submission
    ``webhook_url`` a client passed at submit time. Signed identically to
    deployment webhooks so the same verification works."""
    if not url:
        return {"delivered": 0, "targets": 0}
    body, headers = _build_request(event_type, payload)
    async with httpx.AsyncClient(timeout=15.0) as client:
        ok = await _post_with_retries(client, url, body, headers, max_retries)
    return {"delivered": int(ok), "targets": 1}
