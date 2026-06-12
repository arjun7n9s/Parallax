"""Qdrant vector store for cross-sample semantic search.

Each completed submission gets one 768-dim embedding (nomic-embed-text) built
from its code intent + behavior narrative + visual verdict. Similarity search
over this collection answers "what prior samples look like this one" — the
retrieval that feeds the Intel Correlator and the threat-hunting API.
"""

from __future__ import annotations

import logging

from parallax.ai.llm import llm
from parallax.ai.schemas import CortexResult
from parallax.core.config import settings

logger = logging.getLogger(__name__)

SUBMISSIONS_COLLECTION = "parallax_submissions"
_VECTOR_SIZE = 768


def _client():
    from qdrant_client import QdrantClient

    return QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)


def ensure_collection() -> None:
    from qdrant_client.http.models import Distance, VectorParams

    client = _client()
    existing = {c.name for c in client.get_collections().collections}
    if SUBMISSIONS_COLLECTION not in existing:
        client.create_collection(
            collection_name=SUBMISSIONS_COLLECTION,
            vectors_config=VectorParams(size=_VECTOR_SIZE, distance=Distance.COSINE),
        )
    client.close()


def _summary_text(cortex: CortexResult) -> str:
    parts: list[str] = [cortex.verdict]
    if cortex.code_interpreter:
        parts.append(cortex.code_interpreter.intent_classification)
        parts.extend(cortex.code_interpreter.evidence[:8])
    if cortex.behavior_analyst:
        parts.append(cortex.behavior_analyst.overall_narrative)
    if cortex.visual and cortex.visual.brand_impersonation:
        parts.append(f"impersonates {cortex.visual.brand_impersonation}")
    parts.extend(cortex.attck_techniques)
    return " ".join(p for p in parts if p)


async def index_submission(submission_id: str, sha256: str, cortex: CortexResult) -> bool:
    """Embed and upsert a submission's semantic vector. Returns success."""
    from qdrant_client.http.models import PointStruct

    try:
        ensure_collection()
        text = _summary_text(cortex)
        if not text.strip():
            return False
        vector = (await llm.embed([text]))[0]
        client = _client()
        client.upsert(
            collection_name=SUBMISSIONS_COLLECTION,
            points=[
                PointStruct(
                    id=submission_id,
                    vector=vector,
                    payload={
                        "submission_id": submission_id,
                        "sha256": sha256,
                        "verdict": cortex.verdict,
                        "score": cortex.risk.calibrated_score,
                        "attck": cortex.attck_techniques,
                        "family": (
                            cortex.intel_correlator.family_attribution
                            if cortex.intel_correlator
                            else ""
                        ),
                    },
                )
            ],
        )
        client.close()
        return True
    except Exception as exc:
        logger.warning("Qdrant index failed for %s: %s", submission_id, exc)
        return False


async def search_similar(query: str, top_k: int = 5, exclude_id: str | None = None) -> list[dict]:
    """Return prior submissions semantically similar to the query text."""
    try:
        ensure_collection()
        vector = (await llm.embed([query]))[0]
        client = _client()
        hits = client.query_points(
            collection_name=SUBMISSIONS_COLLECTION,
            query=vector,
            limit=top_k + (1 if exclude_id else 0),
        ).points
        client.close()
        results = []
        for h in hits:
            payload = h.payload or {}
            if exclude_id and payload.get("submission_id") == exclude_id:
                continue
            results.append({**payload, "similarity": round(h.score, 3)})
        return results[:top_k]
    except Exception as exc:
        logger.warning("Qdrant search failed: %s", exc)
        return []
