"""Per-key request rate limiting (Redis fixed-window).

A leaked or abusive API key cannot flood the analysis pipeline: each key (or
client IP when auth is disabled) gets ``RATE_LIMIT_PER_HOUR`` submissions per
clock hour. Redis-backed so the limit holds across API replicas.

Fails *open* if Redis is unreachable — this is an abuse control, not an
authentication boundary (auth still gates access), and availability of the
submission path matters more than strict enforcement during a Redis blip.
"""

from __future__ import annotations

import hashlib
import logging
import time

from fastapi import HTTPException, Request, status

from parallax.core.config import settings

logger = logging.getLogger(__name__)


def _identity(request: Request) -> str:
    """Bucket key: a hash of the API key (never the raw secret), else client IP."""
    key = request.headers.get("X-API-Key")
    if key:
        return "key:" + hashlib.sha256(key.encode()).hexdigest()[:16]
    client = request.client.host if request.client else "unknown"
    return f"ip:{client}"


def check_and_increment(
    client: object, identity: str, limit: int, now_epoch: float
) -> tuple[bool, int]:
    """Fixed-window counter. Returns (allowed, count_after_this_request). Redis
    errors propagate so the caller can decide to fail open."""
    window = int(now_epoch // 3600)
    redis_key = f"rl:{identity}:{window}"
    count = int(client.incr(redis_key))  # type: ignore[attr-defined]
    if count == 1:
        client.expire(redis_key, 3600)  # type: ignore[attr-defined]
    return count <= limit, count


async def rate_limit(request: Request) -> None:
    """FastAPI dependency: enforce the per-key hourly submission budget."""
    limit = settings.RATE_LIMIT_PER_HOUR
    if not limit:
        return  # disabled
    from parallax.workers.heartbeat import get_redis

    try:
        client = get_redis()
        allowed, _ = check_and_increment(client, _identity(request), limit, time.time())
    except Exception as exc:  # noqa: BLE001 - fail open on infra error
        logger.warning("rate limiter unavailable, allowing request: %s", exc)
        return
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {limit} requests/hour for this key.",
            headers={"Retry-After": "3600"},
        )
