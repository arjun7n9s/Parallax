# Scaling

PARALLAX scales by separating API traffic, queue workers, and high-cost dynamic analysis.

## API

Run at least two API replicas behind an ingress or internal load balancer. API pods should
be stateless; uploaded APKs go to object storage, and metadata goes to Postgres.

## Workers

Scale workers by queue pressure and stage latency:

```bash
helm upgrade --install parallax deploy/helm/parallax \
  --set replicaCount.worker=4 \
  --set worker.concurrency=2
```

Keep worker concurrency conservative when dynamic analysis or large decompilation jobs are
enabled. More processes can increase memory pressure faster than throughput.

## Emulator Pool

Android emulators need `/dev/kvm`. On Kubernetes this means:

- Bare-metal or nested-virtualization-capable nodes
- A `nodeSelector` dedicated to emulator workloads
- Privileged emulator pods
- Network policy that blocks direct access to backing services

If KVM nodes are not available, use a managed real-device farm and point dynamic workers at
that device gateway.

## Data Stores

Use managed services for production. Bundled chart datastores are intended for staging,
demo, and isolated validation.
