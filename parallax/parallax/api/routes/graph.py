"""Threat-hunting and knowledge-graph API.

Exposes read-only Cypher, vector similarity search, IoC lookup and structured
hunts over the TAIG graph. All graph reads are guarded against mutating Cypher.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from parallax.knowledge.neo4j_client import neo4j_client
from parallax.knowledge.qdrant_store import search_similar

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graph", tags=["graph"])


class CypherRequest(BaseModel):
    query: str = Field(..., description="Read-only Cypher query")
    params: dict = Field(default_factory=dict)


class SimilarRequest(BaseModel):
    query: str
    top_k: int = 5


class IoCRequest(BaseModel):
    domains: list[str] = Field(default_factory=list)
    ips: list[str] = Field(default_factory=list)


@router.post("/cypher")
async def run_cypher(req: CypherRequest):
    """Execute a read-only Cypher query against the TAIG graph."""
    try:
        rows = await neo4j_client.run_safe_read(req.query, **req.params)
        return {"rows": rows, "count": len(rows)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.warning("Cypher query failed: %s", exc)
        raise HTTPException(status_code=400, detail=f"Query failed: {exc}")


@router.post("/similar")
async def similar(req: SimilarRequest):
    """Find prior submissions semantically similar to a text query."""
    hits = await search_similar(req.query, top_k=req.top_k)
    return {"results": hits}


@router.get("/patterns")
async def list_patterns(category: str | None = None, limit: int = 50):
    """Query the Malware Pattern Memory subsystem."""
    from parallax.knowledge.pattern_memory import CATEGORIES, query_patterns

    if category and category not in CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Unknown category. Valid: {CATEGORIES}")
    patterns = await query_patterns(category=category, limit=limit)
    return {"categories": CATEGORIES, "patterns": patterns, "count": len(patterns)}


@router.post("/find-by-ioc")
async def find_by_ioc(req: IoCRequest):
    """Find APKs that communicated with the given domains/IPs."""
    cypher = """
    MATCH (a:APK)-[:COMMUNICATES_WITH]->(n)
    WHERE (n:Domain AND n.fqdn IN $domains) OR (n:IPAddress AND n.value IN $ips)
    RETURN DISTINCT a.sha256 AS sha256, a.package AS package, a.verdict AS verdict
    LIMIT 100
    """
    rows = await neo4j_client.run_read(cypher, domains=req.domains, ips=req.ips)
    return {"results": rows, "count": len(rows)}
