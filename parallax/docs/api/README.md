# API Documentation

Auto-generated API docs are available at `http://localhost:8000/docs` when the server is running.

## Endpoints

### System
- `GET /health` — Liveness probe
- `GET /ready` — Readiness probe (checks all backing services)

### Analysis (Phase 1+)
- `POST /api/v1/analyze` — Submit APK for analysis
- `GET /api/v1/analysis/{id}` — Get analysis status
- `GET /api/v1/history` — List past analyses
