from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from parallax.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description="GenAI-native automated malware reverse engineering and APK fraud analysis platform",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", tags=["System"])
async def health_check():
    """Basic health check endpoint."""
    return {"status": "ok", "service": settings.PROJECT_NAME}

@app.get("/ready", tags=["System"])
async def readiness_check():
    """Readiness check endpoint. Will eventually check DB/Redis connections."""
    # TODO: Implement DB, Redis, Neo4j, Qdrant connection checks
    return {"status": "ready"}
