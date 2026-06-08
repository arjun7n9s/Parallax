"""
PARALLAX API - Main Application Entry Point

Provides the FastAPI application with health/readiness checks,
CORS middleware, and structured logging.
"""

import logging
from contextlib import asynccontextmanager

import asyncpg
import httpx
import redis as redis_lib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from minio import Minio
from neo4j import GraphDatabase
from qdrant_client import QdrantClient

from parallax.api.routes import analyze_router, status_router
from parallax.core.config import settings
from parallax.core.logging import setup_logging
from parallax.core.storage import init_buckets

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler — runs on startup and shutdown."""
    setup_logging(settings.LOG_LEVEL)
    logger.info(
        "PARALLAX starting",
        extra={"environment": settings.ENVIRONMENT, "version": "0.1.0"},
    )

    # Initialize MinIO buckets
    try:
        init_buckets()
    except Exception as e:
        logger.error(f"Failed to initialize MinIO buckets: {e}")

    yield
    logger.info("PARALLAX shutting down")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description=(
        "GenAI-native automated malware reverse engineering and APK fraud analysis platform"
    ),
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

app.include_router(analyze_router, prefix=settings.API_V1_STR)
app.include_router(status_router, prefix=settings.API_V1_STR)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------ Health
@app.get("/health", tags=["System"])
async def health_check():
    """Basic liveness probe — always returns OK if the process is alive."""
    return {"status": "ok", "service": settings.PROJECT_NAME, "version": "0.1.0"}


# ------------------------------------------------------------------ Ready
@app.get("/ready", tags=["System"])
async def readiness_check():
    """
    Readiness probe — checks connectivity to all backing services.
    Returns 503 if any critical service is unreachable.
    """
    checks: dict[str, str] = {}

    # PostgreSQL
    try:
        conn = await asyncpg.connect(
            host=settings.POSTGRES_SERVER,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            database=settings.POSTGRES_DB,
        )
        await conn.execute("SELECT 1")
        await conn.close()
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = f"error: {e}"

    # Redis
    try:
        r = redis_lib.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)
        r.ping()
        r.close()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    # Neo4j
    try:
        driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
        driver.verify_connectivity()
        driver.close()
        checks["neo4j"] = "ok"
    except Exception as e:
        checks["neo4j"] = f"error: {e}"

    # Qdrant
    try:
        qc = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
        qc.get_collections()
        qc.close()
        checks["qdrant"] = "ok"
    except Exception as e:
        checks["qdrant"] = f"error: {e}"

    # MinIO
    try:
        mc = Minio(
            settings.MINIO_SERVER,
            access_key=settings.MINIO_ROOT_USER,
            secret_key=settings.MINIO_ROOT_PASSWORD,
            secure=settings.MINIO_SECURE,
        )
        mc.list_buckets()
        checks["minio"] = "ok"
    except Exception as e:
        checks["minio"] = f"error: {e}"

    # Ollama
    try:
        resp = httpx.get(f"{settings.OLLAMA_HOST}/api/tags", timeout=5)
        resp.raise_for_status()
        checks["ollama"] = "ok"
    except Exception as e:
        checks["ollama"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    status_code = 200 if all_ok else 503

    return JSONResponse(
        status_code=status_code,
        content={"status": "ready" if all_ok else "degraded", "checks": checks},
    )
