# PARALLAX
**Persistent APK Risk Analysis via Lateral LLM-Augmented eXpertise**

*Multiple perspectives. One persistent truth.*

## Overview

PARALLAX is a GenAI-native automated malware reverse engineering and APK fraud analysis platform. It operates as an autonomous investigator — forming hypotheses, selecting tools, guiding runtime exploration, interpreting code, reconstructing fraud attack chains, and producing evidence-first reports with empirically calibrated risk scores.

Designed specifically for the banking and financial sector.

## Quickstart

1. Ensure Docker and Docker Compose are installed.
2. Clone the repository.
3. Copy and configure your environment:
   ```bash
   cp .env.example .env
   ```
4. Start the infrastructure:
   ```bash
   docker compose up -d
   ```
5. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
6. Initialize the TAIG knowledge graph:
   ```bash
   python scripts/init_neo4j.py
   ```
7. Initialize Qdrant vector collections:
   ```bash
   python scripts/init_qdrant.py
   ```
8. Apply database migrations:
   ```bash
   alembic upgrade head
   ```
8. Start the API server:
   ```bash
   uvicorn parallax.api.main:app --reload
   ```

## API Documentation

Once the server is running, visit `http://localhost:8000/docs` to view the OpenAPI documentation.

## Infrastructure Services

| Service | Port | Purpose |
|---|---|---|
| PostgreSQL | 5432 | Relational metadata |
| Redis | 6379 | Task queue broker |
| MinIO | 9000/9001 | APK & screenshot storage |
| Neo4j | 7474/7687 | TAIG Knowledge Graph |
| Qdrant | 6333/6334 | Vector similarity search |
| Ollama | 11434 | Local LLM serving |
| Grafana | 3000 | Dashboards |
| Prometheus | 9090 | Metrics |
| Jaeger | 16686 | Distributed tracing |

> **Note:** On Linux Docker (non-Desktop), the `prometheus.yml` target `host.docker.internal:8000` may not resolve. Use the container name or network alias instead.
