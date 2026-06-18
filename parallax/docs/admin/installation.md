# Installation

PARALLAX can run locally with Docker Compose or on Kubernetes with Helm.

## Local Development

```bash
cp .env.example .env
docker compose up -d postgres redis minio neo4j qdrant
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m alembic upgrade head
uvicorn parallax.api.main:app --reload
```

Start workers in another terminal:

```bash
celery -A parallax.workers.celery_app worker -Q celery,triage --loglevel=info
```

## Kubernetes

```bash
helm upgrade --install parallax deploy/helm/parallax \
  --namespace parallax --create-namespace \
  --set image.repository=ghcr.io/arjun7n9s/parallax \
  --set image.tag=<git-sha> \
  --set secrets.existingSecret=parallax-runtime
```

The chart runs migrations as a pre-install/pre-upgrade job. Do not run schema migrations
inside application startup.

## Production Shape

For EKS production, prefer managed services:

- RDS Postgres with PITR enabled
- ElastiCache Redis or equivalent
- S3-compatible object storage with versioning and replication
- Managed secrets through External Secrets, Vault, or AWS Secrets Manager
- Dedicated KVM-capable nodes or a real-device farm for dynamic analysis
