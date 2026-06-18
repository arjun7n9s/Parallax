# Bank Audit Security Overview

PARALLAX handles malicious APKs and sensitive analysis data. The security model assumes
uploaded files are hostile and that banks may require strict data residency.

## Architecture Boundaries

| Boundary | Control |
|---|---|
| Upload API | API-key auth, tenant mapping, size cap, APK validation, audit log. |
| Quarantine storage | Uploaded APKs stored separately; raw paths are never exposed. |
| Static workers | Decompilation and static tooling run outside the API process. |
| Dynamic sandbox | APK execution is isolated to emulator/device environments. |
| LLM layer | `LOCAL_ONLY=true` prevents cloud LLM routing. |
| Tenant data | Query paths are tenant-scoped by API key. |

## Data Flow

| Data | Stored In | Sent Externally |
|---|---|---|
| APK binary | Quarantine object storage | No, unless an analyst uses a signed URL internally. |
| Metadata and status | Postgres | No. |
| Static findings | Postgres/object storage | Only to configured LLM provider when cloud routing is enabled. |
| Dynamic observations | Postgres/object storage | Only to configured LLM provider when cloud routing is enabled. |
| Indicators | Postgres, STIX/YARA artifacts, optional MISP | Optional MISP/threat-intel APIs when configured. |
| Traces/metrics | Prometheus/Grafana/Jaeger | No, unless observability is externally hosted. |

## Authentication and Authorization

- `X-API-Key` authenticates analyst requests.
- API keys map to tenants.
- `X-Admin-Key` protects administrative endpoints separately.
- Empty `API_KEY` is development mode only and must not be exposed.
- Signed artifact URLs are short-lived and audited.

## Tenant Isolation

Tenant isolation is enforced in application query paths and by per-tenant SHA deduplication.
A tenant should not be able to read another tenant's submissions, artifacts, graph queries,
or history. Cross-tenant access tests are part of the release gate.

## Malware Handling

- APKs are treated as hostile from upload onward.
- The API host never executes uploaded APKs.
- Dynamic execution belongs in KVM-backed emulator pods or a device farm.
- Production deployments should use Kubernetes network policies so dynamic workloads cannot
reach Postgres, Redis, MinIO/S3, Neo4j, or Qdrant directly.

## LLM Data Residency

Cloud LLM routing is optional. For banks that prohibit code or runtime observations leaving
the environment, set:

```bash
LOCAL_ONLY=true
LLM_MODE=local
```

With `LOCAL_ONLY=true`, all agent calls route to local Ollama-compatible models even if
cloud API keys are present.

## Secrets Management

Local development uses `.env`, which is gitignored. Production should use External Secrets,
Vault, or AWS Secrets Manager and mount a Kubernetes secret such as `parallax-runtime`.

Rotate API keys and provider credentials on a defined schedule, and after any suspected
exposure. Never store provider keys in Helm values committed to git.

## Audit Logging and Retention

Audit events should cover submission, deduplication, artifact access, admin actions, and
security-relevant denials. Retention should match the bank's SOC and regulatory policy.

## Compliance Posture

PARALLAX is designed to support bank vendor assessment controls, but certification depends
on the operator's deployment, policies, and evidence collection.

| Area | Current Control |
|---|---|
| Access control | API keys, tenant mapping, separate admin key. |
| Encryption in transit | TLS at ingress and managed service endpoints. |
| Encryption at rest | Managed Postgres/S3/Kubernetes storage encryption. |
| Auditability | Application audit model and artifact access logging. |
| Data residency | Local-only LLM switch. |
| Disaster recovery | Postgres restore drill and production PITR guidance. |

## Audit Checklist

- Cross-tenant reads return empty or forbidden results.
- Every sensitive API action writes an audit row.
- Rate limits return `429` past quota.
- `LOCAL_ONLY=true` produces no outbound LLM provider calls.
- Emulator egress is restricted to controlled proxy paths.
- Secret values do not appear in logs or CI output.
- Raw APK object paths are not exposed.
- Signed URLs expire according to `SIGNED_URL_TTL_SECONDS`.
