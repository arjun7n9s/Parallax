# PARALLAX Helm Chart

This chart runs the PARALLAX API, Celery workers, migration job, and optional
bundled backing services for staging or kind-style environments.

Production EKS should normally use managed services:

- RDS for Postgres (`postgres.bundled=false`)
- ElastiCache or managed Redis (`redis.bundled=false`)
- S3 or compatible object storage (`minio.bundled=false`)
- Managed/operated Neo4j and Qdrant where available
- External Secrets for all secret values

## Validate

```bash
helm lint deploy/helm/parallax
helm template parallax deploy/helm/parallax --set image.tag=dev >/tmp/parallax.yaml
```

## Install for Staging

```bash
helm upgrade --install parallax deploy/helm/parallax \
  --namespace parallax --create-namespace \
  --set image.repository=ghcr.io/arjun7n9s/parallax \
  --set image.tag=<git-sha> \
  --set secrets.existingSecret=parallax-runtime
```

The migration job runs as a Helm pre-install/pre-upgrade hook, keeping schema
changes outside app startup.

## GitHub Deployment Workflow

`.github/workflows/deploy.yml` deploys the chart with Helm:

- Staging can auto-deploy after a successful `main` CI run when the repo
  variable `STAGING_DEPLOY_ENABLED` is set to `true`.
- Production is manual through `workflow_dispatch` and the `production`
  environment, so required reviewers can be enforced in GitHub settings.
- Store kubeconfigs as base64 secrets:
  `STAGING_KUBECONFIG_B64` and `PRODUCTION_KUBECONFIG_B64`.
- Both environments expect a Kubernetes secret named `parallax-runtime` with
  the runtime values referenced by the chart.

## Android Emulator Nodes

The emulator deployment is disabled by default. Enable it only on nodes that
expose `/dev/kvm`, usually bare-metal EKS instances such as `*.metal`, nested
virtualization-capable nodes, or a real-device farm. Configure:

```yaml
emulator:
  enabled: true
  nodeSelector:
    workload: android-emulator
```
