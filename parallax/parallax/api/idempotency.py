"""Idempotency-Key support for submissions (Redis-backed, 24h TTL).

A client that retries ``POST /analyze`` with the same ``Idempotency-Key`` (e.g.
after a network blip before it saw the response) gets the *same* submission back
instead of creating a duplicate. This complements the sha256 content dedup: it
keys on the client's intent, not the bytes, and short-circuits before the upload
and hashing work.

Stored in Redis with a 24h TTL. Fails open: a Redis outage degrades to "no
idempotency" (the sha256 unique index is still the backstop), never an error.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

IDEM_TTL_SECONDS = 24 * 3600


def _redis_key(idempotency_key: str) -> str:
    return "idem:" + hashlib.sha256(idempotency_key.encode()).hexdigest()[:32]


def lookup_submission_id(client: Any, idempotency_key: str) -> str | None:
    """Return the submission id previously stored for this key, or None."""
    try:
        value = client.get(_redis_key(idempotency_key))
    except Exception as exc:  # noqa: BLE001 - fail open
        logger.warning("idempotency lookup failed, treating as miss: %s", exc)
        return None
    if value is None:
        return None
    return value.decode() if isinstance(value, bytes) else str(value)


def remember_submission_id(
    client: Any, idempotency_key: str, submission_id: str, ttl: int = IDEM_TTL_SECONDS
) -> None:
    """Bind a key to a submission id for ``ttl`` seconds. ``nx=True`` so the
    first writer wins under a concurrent retry race."""
    try:
        client.set(_redis_key(idempotency_key), submission_id, ex=ttl, nx=True)
    except Exception as exc:  # noqa: BLE001 - fail open
        logger.warning("idempotency store failed (non-fatal): %s", exc)
