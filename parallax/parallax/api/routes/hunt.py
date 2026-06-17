"""Structured threat-hunting endpoint.

Translates a small set of high-value hunt intents into safe parameterized
Cypher templates, so analysts can hunt without writing raw graph queries.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from parallax.knowledge.campaign_detection import detect_campaigns
from parallax.knowledge.neo4j_client import neo4j_client

router = APIRouter(prefix="/hunt", tags=["hunt"])

# Named hunts -> parameterized read-only Cypher.
HUNTS: dict[str, str] = {
    "high_risk_apks": (
        "MATCH (a:APK) WHERE a.risk_score >= $min_score "
        "RETURN a.sha256 AS sha256, a.package AS package, a.risk_score AS score, "
        "a.verdict AS verdict ORDER BY a.risk_score DESC LIMIT $limit"
    ),
    "sms_exfiltrators": (
        "MATCH (a:APK)-[:REQUESTS]->(:Permission {name:'android.permission.RECEIVE_SMS'}) "
        "MATCH (a)-[:COMMUNICATES_WITH]->(n) "
        "RETURN DISTINCT a.sha256 AS sha256, a.package AS package, a.verdict AS verdict LIMIT $limit"
    ),
    "shared_c2": (
        "MATCH (a:APK)-[:COMMUNICATES_WITH]->(n)<-[:COMMUNICATES_WITH]-(b:APK) "
        "WHERE a.sha256 < b.sha256 "
        "RETURN a.sha256 AS apk_a, b.sha256 AS apk_b, "
        "labels(n)[0] AS ioc_type, coalesce(n.fqdn, n.value) AS ioc LIMIT $limit"
    ),
    "samples_sharing_c2_with": (
        "MATCH (target:APK {sha256:$sha256})-[:COMMUNICATES_WITH]->(n)"
        "<-[:COMMUNICATES_WITH]-(other:APK) "
        "WHERE other.sha256 <> $sha256 "
        "RETURN DISTINCT other.sha256 AS sha256, other.package AS package, "
        "other.verdict AS verdict, labels(n)[0] AS ioc_type, "
        "coalesce(n.fqdn, n.value) AS ioc ORDER BY sha256 LIMIT $limit"
    ),
    "family_variants": (
        "MATCH (a:APK)-[r:ATTRIBUTED_TO_FAMILY]->(:Family {name:$family}) "
        "RETURN a.sha256 AS sha256, a.package AS package, a.verdict AS verdict, "
        "a.risk_score AS score, r.confidence AS family_confidence "
        "ORDER BY r.confidence DESC, a.risk_score DESC LIMIT $limit"
    ),
    "emerging_campaigns": (
        "MATCH (a:APK)-[:COMMUNICATES_WITH]->(n)<-[:COMMUNICATES_WITH]-(b:APK) "
        "WHERE a.sha256 < b.sha256 "
        "AND coalesce(a.analyzed_at, a.first_seen, datetime()) "
        ">= datetime() - duration({days: $days}) "
        "RETURN a.sha256 AS apk_a, b.sha256 AS apk_b, "
        "labels(n)[0] AS ioc_type, coalesce(n.fqdn, n.value) AS ioc, "
        "coalesce(a.analyzed_at, a.first_seen) AS first_seen "
        "ORDER BY first_seen DESC LIMIT $limit"
    ),
    "bank_impersonators": (
        "MATCH (a:APK)-[r:IMPERSONATES]->(b:BankApp) "
        "RETURN a.sha256 AS sha256, b.name AS bank, r.confidence AS confidence "
        "ORDER BY r.confidence DESC LIMIT $limit"
    ),
    "by_technique": (
        "MATCH (a:APK)-[:USES_TECHNIQUE]->(t:ATTCKTechnique {technique_id:$technique}) "
        "RETURN a.sha256 AS sha256, a.package AS package, a.verdict AS verdict LIMIT $limit"
    ),
}


class HuntRequest(BaseModel):
    hunt: str
    min_score: float = 60.0
    technique: str = ""
    sha256: str = ""
    family: str = ""
    days: int = 7
    limit: int = 50


@router.get("/templates")
async def list_hunts():
    return {"hunts": list(HUNTS.keys())}


@router.post("")
async def run_hunt(req: HuntRequest):
    cypher = HUNTS.get(req.hunt)
    if not cypher:
        return {"error": f"unknown hunt '{req.hunt}'", "available": list(HUNTS.keys())}
    rows = await neo4j_client.run_read(
        cypher,
        min_score=req.min_score,
        technique=req.technique,
        sha256=req.sha256,
        family=req.family,
        days=req.days,
        limit=req.limit,
    )
    return {"hunt": req.hunt, "results": rows, "count": len(rows)}


@router.post("/detect-campaigns")
async def run_campaign_detection(min_size: int = 2):
    """Re-run community detection and return the current campaign clusters."""
    clusters = await detect_campaigns(min_size=min_size)
    return {"campaigns": clusters, "count": len(clusters)}
