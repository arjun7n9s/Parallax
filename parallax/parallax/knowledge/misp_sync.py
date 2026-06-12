"""MISP synchronization for threat-intel sharing.

Pushes one MISP event per analyzed APK (hashes, domains, IPs, URLs) and can pull
recent Android-malware events to seed the corpus. All operations are gated on
``MISP_URL`` / ``MISP_KEY`` being configured and degrade to no-ops otherwise, so
the pipeline runs identically with or without a MISP instance.
"""

from __future__ import annotations

import logging

import httpx

from parallax.ai.schemas import CortexResult
from parallax.core.config import settings

logger = logging.getLogger(__name__)


def _configured() -> bool:
    return bool(settings.MISP_URL and settings.MISP_KEY)


def _headers() -> dict:
    return {
        "Authorization": settings.MISP_KEY,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


async def push_event(sha256: str, package: str, cortex: CortexResult) -> bool:
    """Create a MISP event for a completed analysis. Returns success/no-op."""
    if not _configured():
        logger.debug("MISP not configured; skipping push for %s", sha256)
        return False

    attributes: list[dict] = [
        {"type": "sha256", "category": "Payload delivery", "value": sha256},
    ]
    for dom in cortex.iocs.get("domains", []):
        attributes.append({"type": "domain", "category": "Network activity", "value": dom})
    for ip in cortex.iocs.get("ips", []):
        attributes.append({"type": "ip-dst", "category": "Network activity", "value": ip})
    for url in cortex.iocs.get("urls", []):
        attributes.append({"type": "url", "category": "Network activity", "value": url})

    event = {
        "Event": {
            "info": f"PARALLAX: {package or sha256[:12]} [{cortex.verdict}]",
            "distribution": "0",
            "threat_level_id": "1" if cortex.verdict == "CRITICAL" else "3",
            "analysis": "2",
            "Attribute": attributes,
        }
    }
    try:
        async with httpx.AsyncClient(timeout=20.0, verify=settings.MISP_VERIFY_TLS) as client:
            resp = await client.post(
                f"{settings.MISP_URL.rstrip('/')}/events/add",
                json=event,
                headers=_headers(),
            )
            ok = resp.status_code in (200, 201)
            if not ok:
                logger.warning("MISP push returned %s for %s", resp.status_code, sha256)
            return ok
    except Exception as exc:
        logger.warning("MISP push failed for %s: %s", sha256, exc)
        return False


async def pull_recent_events(days: int = 30, limit: int = 100) -> list[dict]:
    """Pull recent Android-malware events to seed the corpus."""
    if not _configured():
        return []
    try:
        async with httpx.AsyncClient(timeout=30.0, verify=settings.MISP_VERIFY_TLS) as client:
            resp = await client.post(
                f"{settings.MISP_URL.rstrip('/')}/events/restSearch",
                json={"last": f"{days}d", "limit": limit, "tags": ["android", "banking"]},
                headers=_headers(),
            )
            if resp.status_code != 200:
                return []
            return list(resp.json().get("response", []))
    except Exception as exc:
        logger.warning("MISP pull failed: %s", exc)
        return []
