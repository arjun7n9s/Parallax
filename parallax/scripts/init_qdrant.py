#!/usr/bin/env python3
"""
Initialize Qdrant vector collections for PARALLAX.

Creates the collections required for semantic similarity search:
  - parallax_code_intents: Embeddings of decompiled code intent classifications
  - parallax_screenshots:  Embeddings of app screenshots for visual similarity
  - parallax_patterns:     Embeddings of malware behavior patterns

Run this script once after Qdrant is up:
  python scripts/init_qdrant.py
"""

import logging
import os
import sys

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("qdrant_init")

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

# Collection definitions: (name, vector_size, distance_metric)
# Vector sizes chosen to match common embedding models:
#   - 768: sentence-transformers/all-mpnet-base-v2 (code intents, patterns)
#   - 512: CLIP ViT-B/32 (visual embeddings)
COLLECTIONS = [
    ("parallax_code_intents", 768, Distance.COSINE),
    ("parallax_screenshots", 512, Distance.COSINE),
    ("parallax_patterns", 768, Distance.COSINE),
]


def init_qdrant() -> None:
    logger.info("Connecting to Qdrant at %s:%d...", QDRANT_HOST, QDRANT_PORT)
    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

        existing = {c.name for c in client.get_collections().collections}
        logger.info("Existing collections: %s", existing or "(none)")

        for name, size, distance in COLLECTIONS:
            if name in existing:
                logger.info("  ✔ Collection '%s' already exists — skipping", name)
                continue

            logger.info("  Creating collection '%s' (dim=%d, distance=%s)", name, size, distance)
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=size, distance=distance),
            )

        logger.info("✅ All Qdrant collections initialized successfully.")
        client.close()
    except Exception as e:
        logger.error("❌ Failed to initialize Qdrant: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    init_qdrant()
