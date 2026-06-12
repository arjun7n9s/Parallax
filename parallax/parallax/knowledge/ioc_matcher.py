"""IoC-based family attribution (replaces the planned Diaphora binary diffing).

Diaphora needs IDA Pro and a maintained reference corpus. IoC matching answers
the same "what family is this?" question using indicators we already extract,
matched against public threat-intel feeds plus our own growing TAIG corpus. All
external lookups are optional (gated on API keys) and degrade gracefully — the
internal corpus match always runs.
"""

from __future__ import annotations

import logging

import httpx

from parallax.core.config import settings
from parallax.knowledge.neo4j_client import neo4j_client

logger = logging.getLogger(__name__)


async def _query_malwarebazaar(sha256: str) -> dict | None:
    """MalwareBazaar hash lookup. No API key required for hash queries."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://mb-api.abuse.ch/api/v1/",
                data={"query": "get_info", "hash": sha256},
                headers=(
                    {"Auth-Key": settings.MALWAREBAZAAR_API_KEY}
                    if settings.MALWAREBAZAAR_API_KEY
                    else {}
                ),
            )
            data = resp.json()
            if data.get("query_status") != "ok":
                return None
            item = (data.get("data") or [{}])[0]
            return {
                "source": "malwarebazaar",
                "family": item.get("signature") or "",
                "tags": item.get("tags") or [],
                "confidence": 0.9 if item.get("signature") else 0.4,
            }
    except Exception as exc:
        logger.debug("MalwareBazaar lookup failed: %s", exc)
        return None


async def _query_virustotal(sha256: str) -> dict | None:
    if not settings.VIRUSTOTAL_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"https://www.virustotal.com/api/v3/files/{sha256}",
                headers={"x-apikey": settings.VIRUSTOTAL_API_KEY},
            )
            if resp.status_code != 200:
                return None
            attrs = resp.json().get("data", {}).get("attributes", {})
            stats = attrs.get("last_analysis_stats", {})
            label = attrs.get("popular_threat_classification", {}).get(
                "suggested_threat_label", ""
            )
            return {
                "source": "virustotal",
                "family": label,
                "malicious_count": stats.get("malicious", 0),
                "confidence": min(1.0, stats.get("malicious", 0) / 40.0),
            }
    except Exception as exc:
        logger.debug("VirusTotal lookup failed: %s", exc)
        return None


async def _query_internal_corpus(
    domains: list[str], ips: list[str], exclude_sha: str
) -> dict | None:
    """Find prior APKs in TAIG that share network infrastructure with this one."""
    if not domains and not ips:
        return None
    cypher = """
    MATCH (a:APK)-[:COMMUNICATES_WITH]->(n)
    WHERE (n:Domain AND n.fqdn IN $domains) OR (n:IPAddress AND n.value IN $ips)
    WITH a, count(DISTINCT n) AS shared
    WHERE a.sha256 <> $exclude
    RETURN a.sha256 AS sha256, a.package AS package, a.verdict AS verdict, shared
    ORDER BY shared DESC LIMIT 10
    """
    try:
        rows = await neo4j_client.run_read(
            cypher, domains=domains, ips=ips, exclude=exclude_sha
        )
        if not rows:
            return None
        return {
            "source": "internal_corpus",
            "shared_infrastructure_with": rows,
            "confidence": min(1.0, 0.3 + 0.1 * len(rows)),
        }
    except Exception as exc:
        logger.debug("Internal corpus match failed: %s", exc)
        return None


async def match_iocs(
    sha256: str, domains: list[str], ips: list[str]
) -> dict:
    """Aggregate family attribution from all available sources."""
    results: list[dict] = []
    for source in (
        await _query_malwarebazaar(sha256),
        await _query_virustotal(sha256),
        await _query_internal_corpus(domains, ips, sha256),
    ):
        if source:
            results.append(source)

    # Best family guess = highest-confidence source that names a family.
    family = ""
    confidence = 0.0
    for r in results:
        fam = r.get("family")
        if fam and r.get("confidence", 0) > confidence:
            family = fam
            confidence = r.get("confidence", 0)

    return {
        "family": family,
        "confidence": round(confidence, 3),
        "sources": results,
    }
