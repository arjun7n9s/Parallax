import os

from celery import Celery
from celery.signals import worker_process_init

# Setup Celery with Redis broker and backend
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "parallax_workers",
    broker=REDIS_URL,
    backend=REDIS_URL,
    # Explicit include so every pipeline stage registers even when a worker
    # process starts cold (no reliance on transitive imports).
    include=[
        "parallax.workers.triage_worker",
        "parallax.workers.static_worker",
        "parallax.workers.dynamic_worker",
        "parallax.workers.reasoning_worker",
        "parallax.workers.delivery_worker",
        "parallax.workers.reaper",
    ],
)

# Orphan reaper runs on Celery beat: re-queue analyses whose worker died
# mid-stage (heartbeat expired). Interval is configurable; default 30s.
_REAP_INTERVAL = float(os.environ.get("ORPHAN_REAP_INTERVAL", "30"))

# Optional configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Triage gets its own queue so it can scale independently. Workers must
    # listen on both: celery -A parallax.workers.celery_app worker -Q celery,triage
    task_routes={"parallax.workers.triage_worker.*": {"queue": "triage"}},
    beat_schedule={
        "reap-orphans": {
            "task": "parallax.workers.reaper.reap_orphans",
            "schedule": _REAP_INTERVAL,
        }
    },
)


@worker_process_init.connect
def init_worker_telemetry(**kwargs):
    """Initialize OpenTelemetry tracing for the worker process."""
    from parallax.core.telemetry import OTEL_AVAILABLE, init_telemetry

    if OTEL_AVAILABLE:
        try:
            init_telemetry("parallax-worker")
            from opentelemetry.instrumentation.celery import CeleryInstrumentor

            CeleryInstrumentor().instrument()
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(f"Failed to initialize Celery telemetry: {e}")


if __name__ == "__main__":
    celery_app.start()
