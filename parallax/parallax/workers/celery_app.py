import os

from celery import Celery

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
    ],
)

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
)

if __name__ == "__main__":
    celery_app.start()
