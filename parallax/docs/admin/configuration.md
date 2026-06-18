# Configuration

PARALLAX is configured with environment variables. Secrets belong in `.env` for local
development and in a production secret manager for Kubernetes.

## Core

| Variable | Purpose |
|---|---|
| `ENVIRONMENT` | Runtime environment label. |
| `LOG_LEVEL` | Application log level. |
| `LOG_FORMAT` | `json`, `console`, or `auto`. Use `json` in production. |
| `ALLOWED_ORIGINS` | JSON list of frontend origins allowed by CORS. |

## Security and Tenancy

| Variable | Purpose |
|---|---|
| `API_KEY` | Default analyst API key. Empty disables auth for development only. |
| `TENANT_ID` | Tenant mapped to `API_KEY`. |
| `API_KEY_TENANT_MAP` | Comma-separated `key:tenant` pairs for multiple tenants. |
| `ADMIN_API_KEY` | Separate key for admin endpoints. |
| `RATE_LIMIT_PER_HOUR` | Per-key submission budget. `0` disables rate limiting. |
| `SIGNED_URL_TTL_SECONDS` | TTL for signed quarantine URLs. |

## Backing Services

| Variable | Purpose |
|---|---|
| `POSTGRES_SERVER`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Metadata database. |
| `REDIS_HOST`, `REDIS_PORT` | Celery broker and heartbeat store. |
| `MINIO_SERVER`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `MINIO_SECURE` | Object storage. |
| `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` | Threat-analysis graph. |
| `QDRANT_HOST`, `QDRANT_PORT` | Vector similarity store. |

## LLM Routing

| Variable | Purpose |
|---|---|
| `LLM_MODE` | `local`, `cloud`, or `auto`. |
| `LOCAL_ONLY` | Hard-disable cloud LLM routing when `true`. |
| `CLOUD_PROVIDER` | `aiml`, `anthropic`, or `openai`. |
| `AIML_API`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` | Provider credentials. |
| `OLLAMA_HOST` | Local model server endpoint. |

## Analysis Tools

| Variable | Purpose |
|---|---|
| `JADX_BIN` | Optional Jadx binary path. |
| `FLOWDROID_JAR` | Optional FlowDroid jar path. |
| `ANDROID_PLATFORMS_DIR` | Android SDK platforms path for FlowDroid. |
| `YARA_RULES_DIR` | Optional YARA rule directory override. |
| `DYNAMIC_LIVE_DEVICE` | Enable live emulator/device provisioning. |
| `DYNAMIC_TIMEOUT_SECONDS` | Runtime analysis timeout. |
| `MITM_PROXY_HOST`, `MITM_PROXY_PORT` | Controlled proxy target. |
| `FRIDA_DEVICE_ID` | Frida/adb device identifier. |

## Integrations

| Variable | Purpose |
|---|---|
| `WEBHOOK_URLS`, `WEBHOOK_SECRET` | HMAC-signed outbound events. |
| `VIRUSTOTAL_API_KEY`, `MALWAREBAZAAR_API_KEY` | Threat-intel enrichment. |
| `MISP_URL`, `MISP_KEY`, `MISP_VERIFY_TLS` | MISP push/pull integration. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Tracing endpoint. |
