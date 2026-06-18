# Monitoring

PARALLAX exposes API health, queue progress, worker heartbeat, LLM token, and estimated
cost metrics.

## Health Endpoints

| Endpoint | Use |
|---|---|
| `/health` | Process liveness. |
| `/ready` | Backing-service readiness. |
| `/metrics` | Prometheus scrape target. |

## Dashboards

Grafana dashboards cover:

- Submission volume and pipeline status
- Analysis latency by stage
- Worker health and orphan requeue behavior
- LLM token usage and estimated spend
- Backing-service health

## Alerts

Prometheus rules include daily LLM spend thresholding and are tested in CI with
`promtool test rules prometheus_rule_tests.yml`. Alertmanager config is also
validated in CI with `amtool check-config`.

Run the same checks locally:

```bash
docker run --rm -v "$PWD:/workspace" -w /workspace --entrypoint promtool prom/prometheus:v2.51.2 check config prometheus.yml
docker run --rm -v "$PWD:/workspace" -w /workspace --entrypoint promtool prom/prometheus:v2.51.2 test rules prometheus_rule_tests.yml
docker run --rm -v "$PWD:/workspace" -w /workspace --entrypoint amtool prom/alertmanager:v0.27.0 check-config alertmanager.yml
```

Add production alerts for:

- API readiness failure
- Worker heartbeat gaps
- Queue depth growth
- Postgres storage pressure
- MinIO/S3 replication lag
- Emulator node exhaustion

## Useful Checks

```bash
kubectl -n parallax get pods
kubectl -n parallax logs deploy/parallax-api
kubectl -n parallax logs deploy/parallax-worker
kubectl -n parallax get jobs
```
