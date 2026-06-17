"""
Application settings loaded from environment variables and .env file.

All backing-service connection info is centralized here so it's never
string-built in multiple places.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    PROJECT_NAME: str = "PARALLAX"
    API_V1_STR: str = "/api/v1"
    LOG_LEVEL: str = "INFO"
    # Log rendering: "json" for machine ingestion (Loki/ELK), "console" for
    # human-readable colored output, "auto" to pick JSON unless stdout is a TTY.
    LOG_FORMAT: str = "auto"

    # Security
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]
    MAX_UPLOAD_SIZE_MB: int = 500  # Max APK upload size in megabytes
    # API key required (X-API-Key header) on all endpoints except /health and
    # /ready. Empty = auth disabled (development only — never run open in prod).
    API_KEY: str = ""

    # PostgreSQL
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "parallax_db_pass"
    POSTGRES_DB: str = "parallax"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # Liveness heartbeat + orphan reaping. A running stage refreshes a Redis key
    # every HEARTBEAT_INTERVAL seconds with a HEARTBEAT_TTL expiry; the orphan
    # reaper re-queues non-terminal analyses whose heartbeat has expired and that
    # have been untouched for at least ORPHAN_GRACE_SECONDS (guards against
    # re-dispatching a just-queued or just-restarted analysis).
    HEARTBEAT_ENABLED: bool = True
    HEARTBEAT_INTERVAL: float = 10.0
    HEARTBEAT_TTL: int = 30
    ORPHAN_GRACE_SECONDS: int = 90

    # MinIO
    MINIO_SERVER: str = "localhost:9000"
    MINIO_ROOT_USER: str = "admin"
    MINIO_ROOT_PASSWORD: str = "parallax_minio_pass"
    MINIO_SECURE: bool = False

    # Neo4j (TAIG Graph)
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "parallax_neo4j_pass"

    # Qdrant (Vector DB)
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333

    # Ollama (Local LLM)
    OLLAMA_HOST: str = "http://localhost:11434"

    # LLM provider selection. "local" routes every agent to Ollama; "cloud"
    # routes cloud-capable agents to the configured cloud provider; "auto"
    # uses cloud when a key is present and falls back to local otherwise.
    LLM_MODE: str = "local"  # local | cloud | auto
    CLOUD_PROVIDER: str = "aiml"  # aiml | anthropic | openai
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    # aimlapi.com unified gateway: one key, 400+ models, OpenAI-compatible.
    # Per-role model IDs live in parallax.ai.llm.ROSTER.
    AIML_API: str = ""
    AIML_BASE_URL: str = "https://api.aimlapi.com/v1"

    # External analysis tool paths. Empty = resolve from PATH.
    JADX_BIN: str = ""
    FLOWDROID_JAR: str = ""
    # YARA rules directory. Empty = auto-resolve (repo-root or package rules/yara).
    YARA_RULES_DIR: str = ""
    # Android platform jars required by FlowDroid (e.g. $ANDROID_HOME/platforms).
    # Empty = derived from ANDROID_HOME / ANDROID_SDK_ROOT at runtime.
    ANDROID_PLATFORMS_DIR: str = ""
    FLOWDROID_TIMEOUT_SECONDS: int = 300
    # Android SDK / adb. Empty = auto-discover (PATH, ANDROID_HOME, defaults).
    ADB_BIN: str = ""
    # When true, the dynamic worker installs the APK on a live emulator/device,
    # sets up frida-server + mitmproxy CA + proxy, and drives the UI with
    # DroidBot-GPT. When false (default, e.g. in CI), the sandbox runs against a
    # device that is already provisioned, and UI exploration is skipped.
    DYNAMIC_LIVE_DEVICE: bool = False
    DYNAMIC_TIMEOUT_SECONDS: int = 120
    DROIDBOT_MAX_TURNS: int = 20
    # Android global proxy target for the in-process mitmproxy. 127.0.0.1
    # preserves the single-host/default emulator behavior; Docker Desktop/WSL
    # live runs can set this to the host gateway reachable from the emulator.
    MITM_PROXY_HOST: str = "127.0.0.1"
    MITM_PROXY_PORT: int = 8080
    # Frida device id. For an adb-connected emulator/device this is the adb
    # serial (e.g. "localhost:5555"); frida tunnels to frida-server through adb.
    # NOT the TCP "host:27042" form — plain get_device() cannot open that.
    FRIDA_DEVICE_ID: str = "localhost:5555"

    # Delivery: outbound webhooks (comma-separated URLs) + HMAC secret. Optional.
    WEBHOOK_URLS: str = ""
    WEBHOOK_SECRET: str = ""

    # Threat-intel API keys (Phase 5 IoC matching / MISP sync). Optional.
    VIRUSTOTAL_API_KEY: str = ""
    MALWAREBAZAAR_API_KEY: str = ""
    MISP_URL: str = ""
    MISP_KEY: str = ""
    # Verify the MISP server's TLS certificate. Only set false for a
    # self-hosted instance with a self-signed cert on a trusted network.
    MISP_VERIFY_TLS: bool = True

    # OpenTelemetry
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"

    # Derived URLs — single source of truth, never build these inline elsewhere
    @property
    def POSTGRES_URL(self) -> str:
        """Async URL for SQLAlchemy (asyncpg driver)."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
        )

    @property
    def POSTGRES_URL_SYNC(self) -> str:
        """Sync URL for Alembic migrations (psycopg2 driver)."""
        # Ensure we construct the URL dynamically instead of using literal ***
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"
        )

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )


settings = Settings()
