# PARALLAX
Self-Evolving Neural Threat Intelligence Engine for Lateral Analysis

## Overview
PARALLAX is a Generative-AI-orchestrated, multi-agent, self-evolving malware analysis platform designed specifically for banking and financial sector fraud analysis.

## Quickstart

1. Ensure Docker and Docker Compose are installed.
2. Clone the repository.
3. Run `cp .env.example .env` and configure your environment variables.
4. Run `docker compose up -d` to start the infrastructure (Neo4j, Qdrant, Postgres, Redis, MinIO, Ollama).
5. Run `pip install -r requirements.txt` to install Python dependencies.
6. Run `uvicorn parallax.api.main:app --reload` to start the API server.

## API Documentation
Once the server is running, visit `http://localhost:8000/docs` to view the OpenAPI documentation.
