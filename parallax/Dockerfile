# PARALLAX application image — serves both the API and the Celery workers
# (the compose services differ only by command).
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Java for jadx / FlowDroid; build tools for native wheels that lack binaries.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        default-jre-headless \
        gcc \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

# Default: API. The worker service overrides this with a celery command.
CMD ["uvicorn", "parallax.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
