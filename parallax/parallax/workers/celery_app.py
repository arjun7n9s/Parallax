import os

from celery import Celery

# Setup Celery with Redis broker and backend
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "parallax_workers",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["parallax.workers.triage_worker"],
)

# Optional configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={"parallax.workers.triage_worker.*": {"queue": "triage"}},
)

if __name__ == "__main__":
    celery_app.start()
