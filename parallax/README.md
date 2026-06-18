# PARALLAX
**Persistent APK Risk Analysis via Lateral LLM-Augmented eXpertise**

*Multiple perspectives. One persistent truth.*

## Overview

PARALLAX is a GenAI-native automated malware reverse engineering and APK fraud analysis platform. It operates as an autonomous investigator — forming hypotheses, selecting tools, guiding runtime exploration, interpreting code, reconstructing fraud attack chains, and producing evidence-first reports with auditable two-layer risk scores.

Designed specifically for the banking and financial sector.

**Pipeline:** `upload → triage → static (androguard/jadx/YARA/FlowDroid) → dynamic (Frida/mitmproxy/DroidBot-GPT) → AI reasoning cortex (5 agents + debate + risk) → knowledge graph (Neo4j/Qdrant) → delivery (report/STIX/YARA/fraud rules/webhooks)`

## Quickstart

### 1. Infrastructure

```bash
cp .env.example .env          # then review the values
docker compose up -d postgres redis minio neo4j qdrant
```

> Running Ollama natively? Don't start the compose `ollama` service (port clash on 11434). Pull the models: `ollama pull phi3:mini qwen2.5-coder:7b mistral:7b llava:7b nomic-embed-text`

### 2. Python environment + schemas

```bash
python -m venv .venv && . .venv/bin/activate    # Windows: .venv/Scripts/activate
pip install -r requirements.txt
python -m alembic upgrade head
python scripts/init_neo4j.py
python scripts/init_qdrant.py
```

### 3. Run the API **and a worker** (both required)

```bash
# Terminal 1 — API
uvicorn parallax.api.main:app --reload

# Terminal 2 — analysis workers (without this, submissions queue forever)
celery -A parallax.workers.celery_app worker -Q celery,triage --loglevel=info
```

Or run everything in containers instead:

```bash
docker compose --profile app up -d --build    # adds parallax_api + parallax_worker
```

### 4. Verify and analyze an APK

```bash
curl -s http://localhost:8000/ready | python -m json.tool   # all checks "ok"?

# Submit (add -H "X-API-Key: $API_KEY" if API_KEY is set in .env)
curl -s -F "file=@samples/app.apk" http://localhost:8000/api/v1/analyze
# -> {"submission_id": "..."}

curl -s http://localhost:8000/api/v1/analysis/<submission_id>     # queued -> ... -> complete
curl -s http://localhost:8000/api/v1/analysis/<submission_id>/result
curl -s http://localhost:8000/api/v1/analysis/<submission_id>/report.html -o report.html
```

Other artifacts: `/report.pdf`, `/stix`, `/yara`, `/fraud-rules`, `/fraud-chain`, `/irt`. Threat hunting: `POST /api/v1/hunt`, `POST /api/v1/graph/cypher` (read-only Cypher).

### 5. Run the analyst console

```bash
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`, set the API base to `http://127.0.0.1:8000/api/v1`, and enter `X-API-Key` if your `.env` enables API auth. The console supports APK submit, live history/status polling, result detail, artifact downloads, signed quarantine APK URLs, graph health, and hunt templates.

## Configuration highlights (`.env`)

| Variable | Effect |
|---|---|
| `API_KEY` | Required `X-API-Key` header on all endpoints. **Empty = open API (dev only).** |
| `LLM_MODE` | `local` (Ollama), `cloud`, or `auto`. Cloud needs `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`. CPU-only boxes should use cloud for the full cortex. |
| `FLOWDROID_JAR` + `ANDROID_PLATFORMS_DIR` | Enables static taint analysis (Phase 2.5). Skipped gracefully when unset. |
| `DYNAMIC_LIVE_DEVICE` | `true` = install + drive the APK on a rooted emulator/device via adb/Frida/DroidBot. |
| `WEBHOOK_URLS` / `WEBHOOK_SECRET` | HMAC-signed `analysis.completed` / `verdict.critical` events. Always set the secret. |

## Troubleshooting

- **Submission stuck in `queued`** — no Celery worker running, or it isn't listening on the `triage` queue. Start it with `-Q celery,triage`.
- **Cortex times out locally** — 7B models on CPU take minutes per call. Set `LLM_MODE=cloud` with an API key, or run Ollama on a GPU.
- **`/ready` shows a failing check** — that backing service is down; `docker compose ps` and restart it.
- **FlowDroid “platforms directory not found”** — set `ANDROID_PLATFORMS_DIR` (or `ANDROID_HOME`) to an Android SDK `platforms/` dir.
- **Migrations fail on fresh DB** — make sure you run `alembic upgrade head` from the `parallax/` directory so `alembic.ini` is picked up.

## API Documentation

Once the server is running, visit `http://localhost:8000/docs` for the OpenAPI UI.

## Infrastructure Services

| Service | Port | Purpose |
|---|---|---|
| API | 8000 | PARALLAX REST API |
| PostgreSQL | 5432 | Relational metadata |
| Redis | 6379 | Task queue broker |
| MinIO | 9000/9001 | APK & screenshot storage |
| Neo4j | 7474/7687 | TAIG Knowledge Graph |
| Qdrant | 6333/6334 | Vector similarity search |
| Ollama | 11434 | Local LLM serving |
| Grafana | 3000 | Dashboards (auto-provisioned from `grafana/provisioning/`) |
| Prometheus | 9090 | Metrics |
| Jaeger | 16686 | Distributed tracing |

> **Note:** On Linux Docker (non-Desktop), the `prometheus.yml` target `host.docker.internal:8000` may not resolve. Use the container name or network alias instead.

## Development

```bash
python -m pytest tests/unit -q          # unit tests
python -m ruff check parallax/          # lint
python -m mypy parallax/ai parallax/knowledge parallax/delivery
```

Integration tests under `tests/integration/` need live services and auto-skip when unreachable.

## Kubernetes Deployment

The Helm chart lives in `deploy/helm/parallax`. It renders the API, worker,
pre-install/pre-upgrade migration job, and optional bundled backing services for
staging. Production EKS should point the chart at managed Postgres/S3/Redis and
an externally managed secret.

```bash
helm lint deploy/helm/parallax
helm upgrade --install parallax deploy/helm/parallax \
  --namespace parallax --create-namespace \
  --set image.repository=ghcr.io/arjun7n9s/parallax \
  --set image.tag=<git-sha> \
  --set secrets.existingSecret=parallax-runtime
```
