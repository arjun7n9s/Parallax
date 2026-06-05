# PARALLAX  --  Deployment Guide
## From Local Dev to Bank Production

> **V2 NOTE:** This document is part of the original planning suite. The authoritative
> design now lives in:
> - `PARALLAX_VISION.md`  --  anchor vision document
> - `02b_ARCHITECTURE_REVISED.md`  --  revised architecture with hypothesis-driven loop
> - `02_ARCHITECTURE.md`  --  original (this doc references it)
>
> Key v2 additions: AI Reverse Engineering Workbench, Hypothesis Loop, AI-Guided
> Dynamic Exploration, Adaptive Hook Planning, Malware Pattern Memory, Risk
> Calibration Engine, IRT distillation, Fraud Attack Chain, Approval Modes.
> Read `PARALLAX_VISION.md` first for the anchor view.

---

---

## 1. Deployment Tiers

PARALLAX supports three deployment tiers:

| Tier | Use Case | Hardware | Scale |
|---|---|---|---|
| **Local Dev** | Single developer, experimentation | Workstation | 5-20 APKs/day |
| **Pilot** | Pilot with one bank, limited load | 1 server, 1 GPU | 50-100 APKs/day |
| **Production** | Full multi-analyst deployment | K8s cluster, GPU nodes | 500+ APKs/day |

---

## 2. Local Development Deployment

### 2.1 Prerequisites
- Windows 10/11 with WSL2 enabled, OR Linux/macOS
- Docker Desktop (or Docker Engine on Linux)
- Python 3.11+
- 32GB RAM minimum
- 100GB free disk
- (Optional) NVIDIA GPU with 8GB+ VRAM

### 2.2 Quick Start

```bash
# Clone
git clone https://github.com/yourorg/parallax.git
cd parallax

# Copy env template
cp .env.example .env
# Edit .env with secure passwords

# Start all services
docker compose up -d

# Wait for services to be healthy
docker compose ps
# All should show "healthy"

# Install Python deps
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Initialize database
alembic upgrade head

# Pull LLM models (one-time, slow)
ollama pull phi3:mini
ollama pull deepseek-coder-v2:16b
ollama pull llava-onevision

# Run API
uvicorn parallax.api.main:app --reload

# Run worker (in separate terminal)
celery -A parallax.workers.celery_app worker --loglevel=info

# Open browser
open http://localhost:8000/docs
open http://localhost:3000  # Grafana
open http://localhost:7474  # Neo4j Browser
```

### 2.3 Verify Setup

```bash
# Health check
curl http://localhost:8000/health
# {"status": "healthy"}

# Readiness check
curl http://localhost:8000/ready
# {"status": "ready", "components": {"postgres": "ok", "redis": "ok", ...}}

# Submit a test APK
curl -X POST http://localhost:8000/api/v1/analyze \
  -F "apk_file=@tests/fixtures/sample_apks/benign/whatsapp.apk"
# {"submission_id": "...", "triage_score": 15, "priority": "LOW"}
```

---

## 3. Pilot Deployment (Single Server)

### 3.1 Hardware Requirements

| Component | Minimum | Recommended |
|---|---|---|
| CPU | 16 cores | 32 cores |
| RAM | 64 GB | 128 GB |
| GPU | RTX 4090 (24GB) | 1x A100 (80GB) |
| Storage | 2 TB SSD | 4 TB NVMe |
| Network | 1 Gbps | 10 Gbps |
| OS | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |

### 3.2 Architecture (Single Server)

```
┌────────────────────────────────────────────────────────┐
│  Single Server (Ubuntu 24.04)                         │
│                                                        │
│  ┌─────────────────────────────────────────────────┐ │
│  │ Docker Compose Stack                            │ │
│  │                                                  │ │
│  │  nginx (TLS termination, port 443)              │ │
│  │  api (FastAPI, port 8000)                       │ │
│  │  workers (Celery, 4 concurrency)                │ │
│  │  ollama (GPU)                                    │ │
│  │  ┌────────────┐                                  │ │
│  │  │ nginx 443  │ -> api 8000                       │ │
│  │  └────────────┘                                  │ │
│  │  postgres, redis, minio, neo4j, qdrant, grafana │ │
│  └─────────────────────────────────────────────────┘ │
│                                                        │
│  Storage: ZFS or LVM-managed disk                      │
│  Backup: Daily to S3-compatible off-site               │
└────────────────────────────────────────────────────────┘
```

### 3.3 Setup

```bash
# 1. Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 2. Install NVIDIA Container Toolkit (if GPU)
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# 3. Clone and configure
sudo mkdir -p /opt/parallax
sudo chown $USER:$USER /opt/parallax
cd /opt/parallax
git clone https://github.com/yourorg/parallax.git .
cp .env.example .env
# Edit .env with production passwords

# 4. Generate SSL certs (Let's Encrypt or self-signed for pilot)
sudo apt install certbot
sudo certbot certonly --standalone -d parallax.yourbank.com

# 5. Start
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 6. Pull models
docker compose exec ollama ollama pull phi3:mini
docker compose exec ollama ollama pull deepseek-coder-v2:16b
docker compose exec ollama ollama pull llava-onevision

# 7. Initialize
docker compose exec api alembic upgrade head

# 8. Configure systemd service for auto-restart
sudo tee /etc/systemd/system/parallax.service <<EOF
[Unit]
Description=PARALLAX Stack
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/parallax
ExecStart=/usr/bin/docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.yml -f docker-compose.prod.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable parallax
```

### 3.4 Operational Runbooks

#### Daily Operations
```bash
# Check service health
cd /opt/parallax && docker compose ps

# Check recent errors
docker compose logs --since="24h" | grep -i error

# Check disk usage
df -h /opt/parallax

# Check pending analyses
docker compose exec postgres psql -U parallax -c \
  "SELECT count(*), status FROM analyses WHERE submitted_at > NOW() - INTERVAL '1 day' GROUP BY status"
```

#### Weekly Maintenance
```bash
# Backup Neo4j
docker compose exec neo4j neo4j-admin dump --database=neo4j --to=/backups/neo4j-$(date +%Y%m%d).dump

# Backup Postgres
docker compose exec postgres pg_dump -U parallax parallax | gzip > /backups/postgres-$(date +%Y%m%d).sql.gz

# Backup MinIO (APK storage)
docker compose exec minio mc mirror /data /backups/minio-$(date +%Y%m%d)

# Backup retention: 30 days local, 1 year off-site (S3)
```

#### Incident: Worker Stuck
```bash
# Find stuck task
docker compose exec redis redis-cli LRANGE celery:high 0 -1

# Purge stuck queue
docker compose exec redis redis-cli DEL celery:high

# Restart workers
docker compose restart worker
```

#### Incident: Disk Full
```bash
# Find large files in MinIO
docker compose exec minio du -sh /data/* | sort -h | tail

# Purge APKs older than 90 days (configurable)
docker compose exec postgres psql -U parallax -c \
  "DELETE FROM analyses WHERE submitted_at < NOW() - INTERVAL '90 days' RETURNING sha256" | \
  xargs -I {} docker compose exec minio mc rm /data/{}.apk
```

---

## 4. Production Deployment (Kubernetes)

### 4.1 When to Migrate
- Sustained >50 APKs/day
- Multiple concurrent analysts
- HA requirement
- Auto-scaling needed

### 4.2 Architecture

```
┌────────────────────────────────────────────────────────────┐
│                     Kubernetes Cluster                     │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  Namespace: parallax                                  │ │
│  │                                                       │ │
│  │  Deployments:                                         │ │
│  │  - parallax-api (3 replicas, HPA)                     │ │
│  │  - parallax-worker-static (3 replicas)                │ │
│  │  - parallax-worker-dynamic (5 replicas, GPU node)     │ │
│  │  - parallax-worker-ai (2 replicas, GPU node)          │ │
│  │  - parallax-web (React UI, 2 replicas)                │ │
│  │                                                       │ │
│  │  StatefulSets:                                        │ │
│  │  - neo4j (3-node cluster)                             │ │
│  │  - qdrant (3-node cluster)                            │ │
│  │  - minio (4-node distributed)                         │ │
│  │  - postgres (1 primary + 2 replicas)                 │ │
│  │  - redis (3-node parallax)                           │ │
│  │  - ollama (GPU node, 1+ replicas)                    │ │
│  │                                                       │ │
│  │  Services:                                            │ │
│  │  - parallax-api (ClusterIP)                          │ │
│  │  - parallax-web (LoadBalancer)                       │ │
│  │  - Internal service mesh                             │ │
│  │                                                       │ │
│  │  ConfigMaps: env config                              │ │
│  │  Secrets: API keys, certs                            │ │
│  │  PVs: data persistence                               │ │
│  │  NetworkPolicies: strict isolation                   │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  Node Pools:                                               │
│  - general (32 cores, 128GB, 500GB SSD)                    │
│  - gpu-large (32 cores, 256GB, 1x A100 80GB)              │
│  - gpu-xlarge (64 cores, 512GB, 2x H100 80GB)             │
│  - storage (32 cores, 64GB, 20TB HDD)                     │
└────────────────────────────────────────────────────────────┘
```

### 4.3 Hardware Requirements (K8s Production)

| Component | Quantity | Spec |
|---|---|---|
| K8s master nodes | 3 | 8 cores, 16GB, 100GB |
| General worker nodes | 3 | 32 cores, 128GB, 500GB SSD |
| GPU nodes (analysis) | 2 | 32 cores, 256GB, 2x A100 80GB, 1TB NVMe |
| GPU nodes (LLM) | 1 | 64 cores, 512GB, 2x H100 80GB, 1TB NVMe |
| Storage nodes | 3 | 32 cores, 64GB, 20TB HDD (for cold APK storage) |
| **Total compute** | 12 nodes | |

### 4.4 Helm Chart Structure

```
deploy/helm/parallax/
├── Chart.yaml
├── values.yaml
├── values.prod.yaml
├── templates/
│   ├── namespace.yaml
│   ├── api-deployment.yaml
│   ├── api-service.yaml
│   ├── api-ingress.yaml
│   ├── worker-static-deployment.yaml
│   ├── worker-dynamic-deployment.yaml
│   ├── worker-ai-deployment.yaml
│   ├── worker-cortex-deployment.yaml
│   ├── web-deployment.yaml
│   ├── web-service.yaml
│   ├── neo4j-statefulset.yaml
│   ├── qdrant-statefulset.yaml
│   ├── minio-statefulset.yaml
│   ├── postgres-statefulset.yaml
│   ├── redis-statefulset.yaml
│   ├── ollama-deployment.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── networkpolicy.yaml
│   ├── hpa.yaml
│   ├── pvc.yaml
│   ├── serviceaccount.yaml
│   ├── rbac.yaml
│   └── prometheus-rules.yaml
└── README.md
```

### 4.5 Deployment Steps

```bash
# 1. Set up K8s cluster (cloud or on-prem)
#    - AWS EKS, GCP GKE, Azure AKS, or self-managed

# 2. Install ingress controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.11.1/deploy/static/provider/cloud/deploy.yaml

# 3. Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.15.0/cert-manager.yaml

# 4. Install NVIDIA device plugin (for GPU nodes)
helm repo add nvdp https://nvidia.github.io/k8s-device-plugin
helm install nvidia-device-plugin nvdp/nvidia-device-plugin --namespace nvidia-device-plugin --create-namespace

# 5. Create namespace and secrets
kubectl create namespace parallax
kubectl create secret generic parallax-secrets \
  --from-file=./secrets/db-password.txt \
  --from-file=./secrets/neo4j-password.txt \
  --from-file=./secrets/redis-password.txt \
  --from-file=./secrets/minio-access-key.txt \
  --from-file=./secrets/minio-secret-key.txt \
  -n parallax

# 6. Install PARALLAX
helm repo add parallax https://yourorg.github.io/parallax-helm
helm install parallax parallax/parallax \
  -n parallax \
  -f deploy/helm/parallax/values.prod.yaml

# 7. Wait for all pods
kubectl wait --for=condition=ready pod -l app=parallax -n parallax --timeout=600s

# 8. Initialize database
kubectl exec -it -n parallax deployment/parallax-api -- alembic upgrade head

# 9. Pull LLM models
kubectl exec -it -n parallax deployment/ollama -- ollama pull phi3:mini
kubectl exec -it -n parallax deployment/ollama -- ollama pull deepseek-coder-v2:16b
kubectl exec -it -n parallax deployment/ollama -- ollama pull llava-onevision
kubectl exec -it -n parallax deployment/ollama -- ollama pull qwen2.5:72b

# 10. Verify
curl https://parallax.yourbank.com/health
```

### 4.6 Auto-Scaling

HPA configured for:
- API: 3-20 replicas based on CPU/RPS
- Static workers: 3-10 replicas based on queue depth
- Dynamic workers: 5-20 replicas (GPU-bound)
- AI Cortex workers: 2-8 replicas (GPU-bound, expensive)
- Web UI: 2-5 replicas based on CPU

```yaml
# Example HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: parallax-api
  namespace: parallax
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: parallax-api
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "100"
```

### 4.7 Network Policies (Isolation)

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: parallax-isolation
  namespace: parallax
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: parallax
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: parallax
  # NO internet egress  --  analysis workers cannot reach outside
  # except to internal whitelisted test endpoints
```

---

## 5. High Availability

### 5.1 SPOF Elimination

| Component | HA Strategy |
|---|---|
| API | Multiple replicas + load balancer |
| Workers | Queue-based, stateless, N replicas |
| Postgres | 1 primary + 2 streaming replicas + PgBouncer |
| Redis | 3-node cluster with parallax |
| Neo4j | 3-node Causal Cluster (core servers + read replicas) |
| Qdrant | 3-node cluster |
| MinIO | 4-node distributed (erasure coding) |
| Ollama | Multiple replicas + load balancing |

### 5.2 Backup Strategy

- **Postgres**: pg_basebackup every 6 hours + WAL archiving continuously
- **Neo4j**: Daily full backup + continuous transaction log
- **MinIO**: Cross-region replication (if multi-region)
- **Qdrant**: Daily snapshot
- **Retention**: 30 days hot, 1 year cold (S3 Glacier)

### 5.3 Disaster Recovery

- **RPO** (Recovery Point Objective): 1 hour
- **RTO** (Recovery Time Objective): 4 hours
- **DR site**: Replicated to secondary region (warm standby)
- **Drill**: Quarterly DR test

---

## 6. Monitoring & Observability

### 6.1 Metrics (Prometheus + Grafana)

Pre-built dashboards:
- **System Overview**: API rate, queue depth, error rate, latency
- **Pipeline Health**: Per-stage success rate, time per stage
- **GPU Utilization**: Per-node GPU usage, memory, temperature
- **Storage**: Disk usage, growth rate, retention
- **AI Performance**: Per-model latency, token usage, hallucination rate
- **TAIG**: Graph size, query latency, similarity search stats
- **Security**: Failed auth attempts, suspicious uploads

### 6.2 Tracing (Jaeger)

Every analysis request is fully traced:
- Submit -> Triage -> Static -> Dynamic -> Visual -> Cortex -> Synthesis -> Delivery
- Per-agent LLM call traces
- Per-tool execution traces
- Click through from dashboard to individual trace

### 6.3 Logging (Loki + structured)

All logs in JSON, queryable:
```json
{
  "timestamp": "2026-06-04T10:23:45Z",
  "level": "INFO",
  "submission_id": "abc-123",
  "stage": "static_analysis",
  "tool": "androguard",
  "duration_ms": 1240,
  "result_count": 47,
  "agent": "code_interpreter",
  "model": "deepseek-coder-v2:16b",
  "tokens": 1847
}
```

### 6.4 Alerts

PagerDuty / Opsgenie integration:
- API error rate > 5% for 5 min
- Queue depth > 1000 for 10 min
- GPU OOM
- Neo4j cluster down
- Disk > 80% full
- LLM hallucination rate spike
- Failed analysis > 10% over 1 hour

---

## 7. Security Hardening (Production)

### 7.1 Network
- All internal communication mTLS (cert-manager + Istio)
- Analysis workers on isolated VLAN
- No internet egress for analysis pods
- WAF in front of API (ModSecurity or cloud-native)

### 7.2 Authentication & Authorization
- SSO via bank LDAP/SAML (Keycloak as bridge if needed)
- RBAC: analyst, senior_analyst, admin, auditor roles
- MFA mandatory for all users
- API tokens for service-to-service

### 7.3 Secrets Management
- HashiCorp Vault (or cloud KMS)
- No secrets in env vars or code
- Auto-rotation of DB passwords
- All secrets encrypted at rest

### 7.4 Supply Chain Security
- All container images signed (cosign)
- SBOM generated per build (syft)
- Vulnerability scanning in CI (trivy)
- Renovate for automated dep updates
- Pin all versions, no floating tags in prod

### 7.5 Audit Logging
- Every action logged immutably
- User, action, timestamp, IP, result
- Retained for 7 years (compliance)
- Tamper-evident (blockchain or similar for high-security deployments)

---

## 8. Compliance & Regulatory

### 8.1 RBI Requirements
- Data localization: All analysis on-prem in India
- Audit trail: Immutable logs of every action
- CERT-In reporting: Auto-format for incident reports
- Cyber Security Framework: Risk-based controls, regular audits

### 8.2 SEBI CSCRF
- Incident classification and reporting
- Annual audit support
- Cyber resilience testing

### 8.3 DPDP Act 2023
- Data minimization (no unnecessary PII processing)
- Right to erasure (when applicable)
- Consent management
- Breach notification within 72 hours

### 8.4 ISO 27001 / SOC 2 (if pursuing)
- Access controls documented
- Change management process
- Vulnerability management
- Incident response procedures

---

## 9. Cost Estimation (Production)

### 9.1 On-Prem CapEx
- Hardware (as specified): ~₹2-3 crore
- Network infrastructure: ~₹10-15 lakh
- Backup infrastructure: ~₹10-15 lakh
- **Total CapEx: ~₹2.5-3.5 crore**

### 9.2 On-Prem OpEx (Annual)
- Power + cooling: ~₹15-20 lakh
- Maintenance contracts: ~₹10-15 lakh
- Staff (2 engineers): ~₹50-60 lakh
- **Annual OpEx: ~₹75-95 lakh**

### 9.3 Cloud (AWS, example for 500 APKs/day)
- EKS cluster: ~₹8 lakh/month
- EC2 GPU instances (4x A100): ~₹20 lakh/month
- S3, RDS, etc.: ~₹3 lakh/month
- Data transfer: ~₹2 lakh/month
- **Monthly: ~₹33 lakh / Annual: ~₹4 crore**

### 9.4 Cost Optimization
- Reserved/spot instances for 40-60% savings
- Auto-scaling during off-hours
- S3 Intelligent-Tiering for cold APKs
- Quantized models reduce GPU needs

---

## 10. Day-2 Operations

### 10.1 Routine
- Daily health check (automated dashboard)
- Weekly backup verification
- Monthly model update + DSPy recompilation
- Quarterly security review
- Annual DR drill

### 10.2 Updates
- Rolling update strategy
- Blue-green for major versions
- Database migrations: backward-compatible
- Model updates: shadow mode first

### 10.3 Capacity Planning
- Track APKs/day growth
- Project hardware needs quarterly
- Pre-emptively add GPU nodes before saturation

### 10.4 Training
- Initial training for SOC team
- Quarterly updates on new features
- Annual certification

---

*This deployment guide is a living document. Update as architecture evolves.*
