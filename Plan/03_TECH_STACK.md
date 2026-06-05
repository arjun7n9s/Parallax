# PARALLAX  --  Complete Technology Stack
## Every Tool, Every Version, Every Install Command

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

## 1. Master Stack Overview

PARALLAX is built entirely on **open-source, best-in-class tools**. No proprietary malware engine is required. The stack is organized by system layer.

```
Layer 1 (Ingestion)   -> FastAPI, Celery, Redis, MinIO, APKiD, ssdeep
Layer 2 (Analysis)    -> androguard, jadx, apktool, FlowDroid, YARA,
                         Semgrep, BinDiff, Diaphora, Unicorn, Frida,
                         mitmproxy, Scapy, r2pipe, simplify
Layer 2 Visual (2C)   -> LLaVA-OneVision, InternVL, OpenCV, Pillow
Layer 3 (AI Cortex)   -> Ollama, DeepSeek-Coder-V2, Mistral-Large,
                         Llama-3.1-70B, Phi-3-Mini, GPT-4o/Claude,
                         LangGraph, CrewAI, LlamaIndex, DSPy
Layer 4 (Knowledge)   -> Neo4j, Qdrant, MISP, OpenCTI, NebulaGraph
Layer 5 (Delivery)    -> Grafana, React, Jinja2, OpenTelemetry, Jaeger
Infrastructure       -> Docker, Kubernetes, PostgreSQL, Prometheus
```

---

## 2. Layer 1  --  Ingestion & Triage Stack

### 2.1 FastAPI (Ingestion API)

| Attribute | Value |
|---|---|
| Version | 0.115+ |
| Purpose | Async REST API for APK upload + status queries |
| License | MIT |
| Why chosen | Async-native, OpenAPI auto-gen, Pydantic validation |
| Install | `pip install fastapi[standard] uvicorn[standard]` |
| Docs | https://fastapi.tiangolo.com |

### 2.2 Celery + Redis (Task Queue)

| Attribute | Value |
|---|---|
| Celery | 5.4+ |
| Redis | 7.2+ |
| Purpose | Distributed async task execution with priority queues |
| License | BSD |
| Install | `pip install celery[redis] redis` |
| Docker | `redis:7.2-alpine` |
| Why chosen | Battle-tested, supports priority routing, plays well with K8s |

### 2.3 MinIO (APK Storage)

| Attribute | Value |
|---|---|
| Version | RELEASE.2024-09+ |
| Purpose | S3-compatible storage for APK originals + screenshots |
| License | AGPLv3 |
| Docker | `minio/minio:latest` |
| Why chosen | S3 API, on-premise, retention policies |

### 2.4 APKiD (Packer Detection)

| Attribute | Value |
|---|---|
| Version | 3.0+ |
| Repo | https://github.com/rednaga/APKiD |
| Purpose | Detect packer/protector/obfuscator used in APK |
| Install | `pip install apkid` |
| License | BSD-3 |

### 2.5 ssdeep (Fuzzy Hashing)

| Attribute | Value |
|---|---|
| Version | 3.4+ |
| Purpose | Fuzzy hash for similarity pre-check (fast pre-screening) |
| Install | `apt install ssdeep` or `pip install ssdeep` |
| License | GPLv2 |

### 2.6 Triage LLM: Phi-3 Mini

| Attribute | Value |
|---|---|
| Model | microsoft/Phi-3-mini-4k-instruct |
| Size | 3.8B parameters |
| Quantization | Q4_K_M (GGUF) for CPU, or Q8 for GPU |
| Purpose | Fast pre-scoring from manifest + permissions (<2 seconds) |
| Deployment | Ollama (local) |
| License | MIT |
| Why chosen | Tiny, fast, surprisingly good at structured tasks |
| Pull command | `ollama pull phi3:mini` |

### 2.7 PostgreSQL (Metadata DB)

| Attribute | Value |
|---|---|
| Version | 16+ |
| Purpose | Submission metadata, audit log, IOC storage |
| License | PostgreSQL |
| Docker | `postgres:16-alpine` |

---

## 3. Layer 2  --  Analysis Engine Stack

### 3.1 Static Analysis Toolchain

#### androguard (Python APK/DEX Parser)

| Attribute | Value |
|---|---|
| Version | 4.1+ |
| Repo | https://github.com/androguard/androguard |
| Purpose | Pure-Python APK/DEX disassembly, call graph extraction |
| Install | `pip install androguard` |
| License | Apache 2.0 |
| Python API example | `from androguard.misc import AnalyzeAPK; a, d, dx = AnalyzeAPK("app.apk")` |

#### jadx (Java Decompiler)

| Attribute | Value |
|---|---|
| Version | 1.5.0+ |
| Repo | https://github.com/skylot/jadx |
| Purpose | DEX -> readable Java source |
| License | Apache 2.0 |
| Install | Download release ZIP or `apt install jadx` |
| CLI usage | `jadx -d output_dir app.apk` |

#### apktool (Resource Decoding)

| Attribute | Value |
|---|---|
| Version | 2.9+ |
| Repo | https://github.com/iBotPeaches/Apktool |
| Purpose | Decode resources, manifest, smali |
| License | Apache 2.0 |
| Install | Download jar or `apt install apktool` |

#### FlowDroid (Taint Analysis)

| Attribute | Value |
|---|---|
| Version | 2.13+ |
| Repo | https://github.com/secure-software-engineering/FlowDroid |
| Purpose | Precise data-flow analysis: SOURCE -> SINK |
| License | LGPL |
| Install | Requires Java 11+, download from releases |
| Why chosen | Industry-standard for Android taint analysis |

#### Semgrep (Code Pattern Scanner)

| Attribute | Value |
|---|---|
| Version | 1.90+ |
| Repo | https://github.com/semgrep/semgrep |
| Purpose | Custom rules for banking malware patterns |
| License | LGPL |
| Install | `pip install semgrep` |
| Custom rules | `rules/banking_malware.yml` (in our repo) |

#### YARA (Pattern Engine)

| Attribute | Value |
|---|---|
| Version | 4.5+ |
| Repo | https://github.com/VirusTotal/yara |
| Purpose | Industry-standard malware pattern rules |
| License | BSD-3 |
| Install | `pip install yara-python` |
| Critical | Used in feedback loop  --  auto-generated rules added over time |

#### BinDiff (Binary Diffing)

| Attribute | Value |
|---|---|
| Version | 8 (commercial, free for non-commercial) |
| Alt (open) | Diaphora  --  https://github.com/eshard/diaphora |
| Purpose | Find shared code between APK and known malware |
| License | Commercial (BinDiff) / GPL (Diaphora) |
| Why Diaphora | Open-source, works on APK contexts |

#### Diaphora (Open Binary Diffing)

| Attribute | Value |
|---|---|
| Repo | https://github.com/eshard/diaphora |
| Purpose | Free BinDiff alternative, IDA Pro plugin or standalone |
| License | GPLv2 |
| Why chosen | Open, works on stripped binaries |

#### Unicorn Engine (CPU Emulation)

| Attribute | Value |
|---|---|
| Version | 2.0+ |
| Repo | https://github.com/unicorn-engine/unicorn |
| Purpose | Emulate obfuscated decryptor routines without full OS |
| Install | `pip install unicorn` |
| License | BSD |
| Use case | Run encrypted code blocks, extract decrypted URLs/payloads |

#### r2pipe (Radare2 Python Binding)

| Attribute | Value |
|---|---|
| Version | 5.9+ |
| Repo | https://github.com/radareorg/radare2 |
| Purpose | Binary-level analysis of native .so libraries |
| Install | `pip install r2pipe` + `apt install radare2` |
| License | LGPL |

#### simplify (Android Deobfuscator)

| Attribute | Value |
|---|---|
| Repo | https://github.com/CalebFenton/simplify |
| Purpose | Undo ProGuard/DexGuard/Allatori transformations |
| License | MIT |
| Install | Download JAR from releases |

#### NetworkX (Graph Analysis)

| Attribute | Value |
|---|---|
| Version | 3.3+ |
| Purpose | Permission-API-call graph construction + analysis |
| Install | `pip install networkx` |
| License | BSD |

### 3.2 Dynamic Analysis Toolchain

#### Frida (Runtime Instrumentation)

| Attribute | Value |
|---|---|
| Version | 16.3+ |
| Repo | https://github.com/frida/frida |
| Purpose | Hook any Android function at runtime |
| Install | `pip install frida-tools` |
| License | wxWindows |
| Why chosen | Industry standard, JS/Python API, comprehensive |
| Hook library | `hooks/` directory (custom + community) |

#### mitmproxy (Traffic Interception)

| Attribute | Value |
|---|---|
| Version | 11+ |
| Repo | https://github.com/mitmproxy/mitmproxy |
| Purpose | HTTPS traffic interception + decode |
| Install | `pip install mitmproxy` |
| License | MIT |

#### Scapy (Custom Protocol Analysis)

| Attribute | Value |
|---|---|
| Version | 2.5+ |
| Purpose | Decode non-HTTP C2 protocols (binary, custom) |
| Install | `pip install scapy` |
| License | GPL |

#### Android AVD (Emulator)

| Attribute | Value |
|---|---|
| Component | `emulator` from Android SDK |
| Version | API 33+ image (x86_64) |
| Purpose | Headless sandboxed execution |
| Install | `sdkmanager "emulator" "system-images;android-33;google_apis;x86_64"` |
| Headless | `emulator -avd <name> -no-window -no-audio -no-boot-anim` |

#### Strace / ltrace

| Attribute | Value |
|---|---|
| Strace | https://github.com/strace/strace |
| ltrace | http://www.ltrace.org/ |
| Purpose | System call tracing, native library calls |
| Install | `apt install strace ltrace` |

### 3.3 Visual AI Toolchain

#### LLaVA-OneVision (Multimodal LLM)

| Attribute | Value |
|---|---|
| Model | llava-onevision-qwen2-7b-ov |
| Size | 7B (or 13B for higher accuracy) |
| Purpose | Screenshot analysis for phishing UI detection |
| Deployment | Ollama |
| License | Apache 2.0 |
| Pull command | `ollama pull llava-onevision` |
| Why chosen | State-of-the-art open multimodal, strong on UI analysis |

#### InternVL 2.0 (Alternative Multimodal)

| Attribute | Value |
|---|---|
| Model | internvl2-26b or internvl2-8b |
| Purpose | Alternative to LLaVA, sometimes better on documents |
| Deployment | Ollama or vLLM |
| License | MIT |

#### OpenCV

| Attribute | Value |
|---|---|
| Version | 4.10+ |
| Purpose | Image diffing, pixel-level comparison |
| Install | `pip install opencv-python` |
| License | Apache 2.0 |

#### Pillow

| Attribute | Value |
|---|---|
| Version | 10+ |
| Purpose | Image pre-processing |
| Install | `pip install pillow` |
| License | HPND |

---

## 4. Layer 3  --  AI Reasoning Cortex Stack

### 4.1 LLM Models (All Local via Ollama Unless Noted)

| Model | Size | Quant | Purpose | Ollama Tag |
|---|---|---|---|---|
| Phi-3 Mini | 3.8B | Q4_K_M | Triage pre-scorer | `phi3:mini` |
| DeepSeek-Coder-V2 | 16B | Q4_K_M | Code interpretation | `deepseek-coder-v2:16b` |
| Mistral-Large | 123B | Q4 | Behavior analysis (or use 22B variant) | `mistral-large:latest` |
| Llama-3.1-70B-Instruct | 70B | Q4 | Behavior analysis (alt) | `llama3.1:70b-instruct-q4_K_M` |
| LLaVA-OneVision | 7B | Q4_K_M | Visual UI analysis | `llava-onevision` |
| Qwen2.5-72B | 72B | Q4 | Synthesis (alt, fully local) | `qwen2.5:72b` |
| GPT-4o (API) |  --  |  --  | Synthesis (optional, API) | external |
| Claude Opus (API) |  --  |  --  | Synthesis (optional, API) | external |

**Hardware note for 70B+ models:** Requires 2x NVIDIA A100 80GB or 1x H100 80GB for full speed. For CPU fallback, expect 5-10x slower.

### 4.2 Ollama (LLM Serving)

| Attribute | Value |
|---|---|
| Version | 0.4+ |
| Repo | https://github.com/ollama/ollama |
| Purpose | Local LLM serving (one binary, many models) |
| License | MIT |
| Install | `curl -fsSL https://ollama.com/install.sh \| sh` |
| Docker | `ollama/ollama:latest` |
| Why chosen | Simplest local LLM deployment, model management built in |

### 4.3 LangGraph (Agent Orchestration)

| Attribute | Value |
|---|---|
| Version | 0.2+ |
| Repo | https://github.com/langchain-ai/langgraph |
| Purpose | Stateful multi-agent graph orchestration |
| License | MIT |
| Install | `pip install langgraph langchain` |
| Why chosen | Built for complex agent workflows with state, branches, cycles |

### 4.4 CrewAI (Agent Teams)

| Attribute | Value |
|---|---|
| Version | 0.80+ |
| Repo | https://github.com/crewAIInc/crewAI |
| Purpose | Role-based agent team management |
| License | MIT |
| Install | `pip install crewai` |
| Use case | Alternative agent framework for some workflows |

### 4.5 LlamaIndex (RAG)

| Attribute | Value |
|---|---|
| Version | 0.12+ |
| Repo | https://github.com/run-llama/llama_index |
| Purpose | RAG over MITRE ATT&CK, MISP, threat reports |
| License | MIT |
| Install | `pip install llama-index` |

### 4.6 DSPy (Compiled LLM Pipelines)

| Attribute | Value |
|---|---|
| Version | 2.5+ |
| Repo | https://github.com/stanfordnlp/dspy |
| Purpose | Compiled optimized LLM pipelines (not raw prompting) |
| License | Apache 2.0 |
| Install | `pip install dspy` |
| Why chosen | Prompts are *compiled* against labeled data, not hand-tuned |

---

## 5. Layer 4  --  Knowledge Graph Stack

### 5.1 Neo4j (Primary Graph)

| Attribute | Value |
|---|---|
| Version | 5.20+ (Community or Enterprise) |
| License | GPLv3 (Community) / Commercial (Enterprise) |
| Purpose | TAIG structural knowledge graph |
| Docker | `neo4j:5.20-community` |
| Drivers | `pip install neo4j` (Python) |
| Browser UI | http://localhost:7474 |

### 5.2 Qdrant (Vector Search)

| Attribute | Value |
|---|---|
| Version | 1.10+ |
| License | Apache 2.0 |
| Purpose | Semantic vector search for APK/code similarity |
| Docker | `qdrant/qdrant:latest` |
| Install client | `pip install qdrant-client` |
| Why chosen | Fast, easy to operate, great Python client |

### 5.3 MISP (Threat Intel Platform)

| Attribute | Value |
|---|---|
| Version | 2.4+ |
| Repo | https://github.com/MISP/MISP |
| Purpose | Threat intel sharing, IOC correlation |
| License | AGPL |
| Docker | `coolab/misp-docker` or official |
| API | REST + PyMISP Python client |

### 5.4 NebulaGraph (Scale Option)

| Attribute | Value |
|---|---|
| Version | 3.8+ |
| License | Apache 2.0 |
| Purpose | Scale-out option for billions of graph edges |
| Use case | When Neo4j becomes the bottleneck |

### 5.5 OpenCTI (Alternative Threat Intel)

| Attribute | Value |
|---|---|
| Version | 6.x |
| Repo | https://github.com/OpenCTI-Platform/opencti |
| License | Apache 2.0 |
| Purpose | Alternative threat intel platform with better UI |
| Use case | For client-facing threat intel portal |

---

## 6. Layer 5  --  Delivery Stack

### 6.1 Grafana (Dashboard)

| Attribute | Value |
|---|---|
| Version | 11+ |
| License | AGPL |
| Docker | `grafana/grafana:latest` |
| Purpose | Real-time threat dashboard, metrics visualization |

### 6.2 React (Custom Web UI)

| Attribute | Value |
|---|---|
| Version | 18+ |
| Purpose | Custom analyst interface (APK upload, results view) |
| Build | Vite |
| State | Zustand or Redux |
| License | MIT |
| Why custom | Grafana is for metrics, custom UI for analyst workflow |

### 6.3 Jinja2 (Report Templates)

| Attribute | Value |
|---|---|
| Version | 3.1+ |
| Purpose | PDF report generation from templates |
| Install | `pip install jinja2 weasyprint` |
| License | BSD |

### 6.4 OpenTelemetry (Observability)

| Attribute | Value |
|---|---|
| Version | 1.27+ |
| Purpose | Distributed tracing of every analysis decision |
| Install | `pip install opentelemetry-api opentelemetry-sdk` |
| Why chosen | Vendor-neutral, integrates with everything |

### 6.5 Jaeger (Tracing Backend)

| Attribute | Value |
|---|---|
| Version | 1.60+ |
| Docker | `jaegertracing/all-in-one:latest` |
| Purpose | View distributed traces |

### 6.6 Prometheus (Metrics)

| Attribute | Value |
|---|---|
| Version | 2.54+ |
| Docker | `prom/prometheus:latest` |
| Purpose | Time-series metrics |

### 6.7 Loki (Log Aggregation)

| Attribute | Value |
|---|---|
| Version | 3.3+ |
| Purpose | Centralized log search |

---

## 7. Infrastructure Stack

### 7.1 Docker & Docker Compose

| Component | Version | Purpose |
|---|---|---|
| Docker Engine | 25+ | Container runtime |
| Docker Compose | 2.27+ | Local multi-container orchestration |
| Why | Industry standard, easy local dev |

### 7.2 Kubernetes (Production)

| Component | Version | Purpose |
|---|---|---|
| Kubernetes | 1.30+ | Production orchestration |
| Helm | 3.15+ | Package management |
| Kustomize | 5.4+ | Config management |
| Why | Banks already run K8s; needed for scale |

### 7.3 Supporting Infrastructure

| Tool | Version | Purpose |
|---|---|---|
| Nginx | 1.27+ | Reverse proxy, TLS termination |
| Certbot | 2.11+ | Let's Encrypt cert management |
| HashiCorp Vault | 1.17+ | Secrets management |
| HashiCorp Consul | 1.19+ | Service discovery (optional) |

---

## 8. Frontend Stack (Custom Analyst UI)

```
React 18 + TypeScript
├── Vite (build tool)
├── Tailwind CSS (styling)
├── shadcn/ui (component library)
├── React Query (API state)
├── Zustand (client state)
├── Recharts (charts/graphs)
├── react-cytoscapejs (TAIG graph visualization)
├── Monaco Editor (code viewer)
└── Axios (HTTP)
```

---

## 9. Complete Python `requirements.txt`

```txt
# Layer 1: Ingestion
fastapi==0.115.0
uvicorn[standard]==0.30.6
celery[redis]==5.4.0
redis==5.0.8
minio==7.2.7
apkid==3.0.0
ssdeep==3.4.1
psycopg2-binary==2.9.9
sqlalchemy==2.0.34
alembic==1.13.2
pydantic==2.9.0
pydantic-settings==2.5.2
python-multipart==0.0.10
httpx==0.27.2

# Layer 2A: Static Analysis
androguard==4.1.2
apkutils==0.2.1
networkx==3.3

# Layer 2B: Dynamic Analysis
frida-tools==13.0.0
mitmproxy==11.0.0
scapy==2.5.0
adb-shell==0.4.4
pure-python-adb==0.3.0
selenium==4.25.0  # for UI automation fallback

# Layer 2C: Visual
opencv-python==4.10.0.84
pillow==10.4.0
sentence-transformers==3.1.1  # for CLIP embeddings

# Layer 3: AI Cortex
ollama==0.3.3
langgraph==0.2.16
langchain==0.2.16
langchain-community==0.2.16
crewai==0.80.0
llama-index==0.12.0
llama-index-llms-ollama==0.3.0
dspy==2.5.0
openai==1.51.0
anthropic==0.36.0

# Layer 4: Knowledge
neo4j==5.24.0
qdrant-client==1.10.0
pymisp==2.4.200

# Layer 5: Delivery
jinja2==3.1.4
weasyprint==63.1
reportlab==4.2.2
stix2==3.0.1

# Observability
opentelemetry-api==1.27.0
opentelemetry-sdk==1.27.0
opentelemetry-instrumentation-fastapi==0.48b0
opentelemetry-instrumentation-celery==0.48b0
opentelemetry-exporter-otlp==1.27.0
prometheus-client==0.21.0
structlog==24.4.0

# Utilities
python-dotenv==1.0.1
tenacity==9.0.0
pyyaml==6.0.2
rich==13.9.1
tqdm==4.66.5
pytest==8.3.3
pytest-asyncio==0.24.0
pytest-cov==5.0.0
mypy==1.11.2
ruff==0.6.4
```

---

## 10. Docker Compose Skeleton (Local Dev)

```yaml
version: '3.8'

services:
  redis:
    image: redis:7.2-alpine
    ports: ["6379:6379"]
    volumes: [redis_data:/data]

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: parallax
      POSTGRES_USER: parallax
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports: ["5432:5432"]
    volumes: [pg_data:/var/lib/postgresql/data]

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_PASSWORD}
    ports: ["9000:9000", "9001:9001"]
    volumes: [minio_data:/data]

  neo4j:
    image: neo4j:5.20-community
    environment:
      NEO4J_AUTH: neo4j/${NEO4J_PASSWORD}
    ports: ["7474:7474", "7687:7687"]
    volumes: [neo4j_data:/data]

  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333", "6334:6334"]
    volumes: [qdrant_data:/qdrant/storage]

  ollama:
    image: ollama/ollama:latest
    ports: ["11434:11434"]
    volumes: [ollama_data:/root/.ollama]
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]

  grafana:
    image: grafana/grafana:latest
    ports: ["3000:3000"]
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}

  jaeger:
    image: jaegertracing/all-in-one:latest
    ports: ["16686:16686", "14250:14250"]

  prometheus:
    image: prom/prometheus:latest
    ports: ["9090:9090"]
    volumes: [./prometheus.yml:/etc/prometheus/prometheus.yml]

  api:
    build: ./docker/api
    ports: ["8000:8000"]
    environment:
      DATABASE_URL: postgresql://parallax:${DB_PASSWORD}@postgres:5432/parallax
      REDIS_URL: redis://redis:6379/0
      MINIO_URL: minio:9000
      NEO4J_URL: bolt://neo4j:7687
      QDRANT_URL: http://qdrant:6333
      OLLAMA_URL: http://ollama:11434
    depends_on: [redis, postgres, minio, neo4j, qdrant, ollama]

  worker-static:
    build: ./docker/worker
    command: celery -A parallax.workers.static worker -Q static -l info
    environment:
      DATABASE_URL: postgresql://parallax:${DB_PASSWORD}@postgres:5432/parallax
      REDIS_URL: redis://redis:6379/0
      MINIO_URL: minio:9000
    depends_on: [redis, postgres, minio]

  worker-dynamic:
    build: ./docker/worker-dynamic
    command: celery -A parallax.workers.dynamic worker -Q dynamic -l info
    privileged: true  # needed for emulator + frida
    environment:
      DATABASE_URL: postgresql://parallax:${DB_PASSWORD}@postgres:5432/parallax
      REDIS_URL: redis://redis:6379/0
    depends_on: [redis, postgres]
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]

  worker-ai:
    build: ./docker/worker-ai
    command: celery -A parallax.workers.ai_cortex worker -Q ai -l info
    environment:
      DATABASE_URL: postgresql://parallax:${DB_PASSWORD}@postgres:5432/parallax
      REDIS_URL: redis://redis:6379/0
      OLLAMA_URL: http://ollama:11434
      NEO4J_URL: bolt://neo4j:7687
      QDRANT_URL: http://qdrant:6333
    depends_on: [redis, postgres, ollama, neo4j, qdrant]

volumes:
  redis_data:
  pg_data:
  minio_data:
  neo4j_data:
  qdrant_data:
  ollama_data:
```

---

## 11. Hardware Requirements

### 11.1 Minimum (Development / Single-Analyst)

| Component | Spec |
|---|---|
| CPU | 8 cores, x86_64 |
| RAM | 32 GB |
| GPU | NVIDIA RTX 3060 (12GB)  --  optional but recommended for LLMs |
| Storage | 500 GB SSD |
| Network | 1 Gbps |
| Use case | Single analyst workstation, low volume |

### 11.2 Recommended (Bank Production)

| Component | Spec |
|---|---|
| CPU | 32+ cores per node, 3-5 K8s nodes |
| RAM | 256 GB per node |
| GPU | 2x NVIDIA A100 80GB OR 1x H100 80GB (for 70B LLMs) |
| Storage | 10 TB NVMe SSD (APK storage + graph DB) |
| Network | 10 Gbps internal, dedicated analysis VLAN |
| Use case | 100+ APKs/day, multiple analysts |

### 11.3 Budget (Startup / Pilot)

| Component | Spec |
|---|---|
| CPU | 16 cores |
| RAM | 64 GB |
| GPU | RTX 4090 (24GB)  --  runs 7B/13B models comfortably |
| Storage | 2 TB SSD |
| Use case | Pilot with 5-20 APKs/day |

### 11.4 GPU Memory by Model

| Model | Min VRAM | Recommended VRAM |
|---|---|---|
| Phi-3 Mini (3.8B Q4) | 3 GB | 4 GB |
| DeepSeek-Coder-V2 (16B Q4) | 12 GB | 16 GB |
| Mistral-Large (123B Q4) | 80 GB | 96 GB |
| Llama-3.1-70B (Q4) | 48 GB | 64 GB |
| LLaVA-OneVision (7B) | 8 GB | 12 GB |
| LLaVA-OneVision (13B) | 14 GB | 18 GB |

For CPU-only fallback: expect 5-10x slower inference. Acceptable for batch, not for interactive triage.

---

## 12. Cloud Deployment Options

### 12.1 On-Premise (Recommended for Banks)
- Data never leaves the bank
- Full control over infrastructure
- Compliance-friendly (RBI data localization)
- Higher upfront cost, lower long-term

### 12.2 AWS
- EC2 GPU instances (p4d, p5) for LLM serving
- EKS for orchestration
- S3 for APK storage
- RDS for PostgreSQL
- Neptune for Neo4j alternative
- Compliance: MeitY empaneled for sensitive workloads (verify)

### 12.3 GCP
- A2/A3 instances with A100/H100
- GKE for orchestration
- Cloud Storage for APK blobs
- Cloud SQL for PostgreSQL
- Strong AI/ML tooling (Vertex AI optional)

### 12.4 Azure
- ND A100 v4 series
- AKS for orchestration
- Blob Storage for APKs
- Azure Database for PostgreSQL
- Azure OpenAI Service for synthesis (alternative to local LLM)

### 12.5 Hybrid
- Sensitive analysis on-prem
- Non-sensitive LLM inference in cloud
- Pattern works for banks with hybrid strategy

---

## 13. Dependency Conflict Notes

### 13.1 Known Issues & Resolutions

| Issue | Resolution |
|---|---|
| `numpy` version conflict (andorguard vs scapy vs opencv) | Pin `numpy<2.0` for compatibility |
| `frida-tools` requires matching `frida` server on device | Version pin both at 16.3.3 |
| `langchain` and `langgraph` rapid releases | Pin to specific tested versions |
| `llama-index` sub-packages | Use `llama-index-llms-ollama` etc. |
| `tensorflow` (if used for embeddings) | Avoid; use `sentence-transformers` (PyTorch) instead |

### 13.2 Python Version
- **Required**: Python 3.11+
- **Tested**: 3.11.15, 3.12.x
- **Avoid**: 3.13 (some libs not yet compatible)

### 13.3 CUDA
- Recommended: CUDA 12.x with matching PyTorch
- For Ollama GPU: install NVIDIA Container Toolkit

---

## 14. Repository Structure (Recommended)

```
parallax/
├── README.md
├── LICENSE
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── security-scan.yml
├── parallax/
│   ├── __init__.py
│   ├── api/                    # FastAPI app
│   │   ├── main.py
│   │   ├── routes/
│   │   │   ├── analyze.py
│   │   │   ├── status.py
│   │   │   ├── graph.py
│   │   │   └── hunt.py
│   │   └── schemas/
│   ├── workers/                # Celery workers
│   │   ├── static.py
│   │   ├── dynamic.py
│   │   ├── visual.py
│   │   └── ai_cortex.py
│   ├── analysis/               # Analysis modules
│   │   ├── static/
│   │   │   ├── androguard_runner.py
│   │   │   ├── flowdroid_runner.py
│   │   │   ├── semgrep_runner.py
│   │   │   ├── yara_runner.py
│   │   │   ├── binary_diff.py
│   │   │   └── permission_graph.py
│   │   ├── dynamic/
│   │   │   ├── avd_orchestrator.py
│   │   │   ├── frida_hooks/
│   │   │   ├── mitm_proxy.py
│   │   │   ├── droidbot_gpt.py
│   │   │   └── mutation_runner.py
│   │   └── visual/
│   │       ├── screenshot_capture.py
│   │       └── visual_analyzer.py
│   ├── ai_cortex/              # AI agent layer
│   │   ├── agents/
│   │   │   ├── code_interpreter.py
│   │   │   ├── behavior_analyst.py
│   │   │   ├── intel_correlator.py
│   │   │   ├── visual_intelligence.py
│   │   │   └── synthesis.py
│   │   ├── debate_layer.py
│   │   ├── orchestration.py
│   │   └── prompts/
│   ├── knowledge/              # TAIG
│   │   ├── neo4j_client.py
│   │   ├── schema.py
│   │   ├── population.py
│   │   ├── queries.py
│   │   ├── qdrant_client.py
│   │   └── misp_sync.py
│   ├── delivery/               # Output layer
│   │   ├── report_generator.py
│   │   ├── stix_exporter.py
│   │   ├── yara_generator.py
│   │   ├── webhook_dispatcher.py
│   │   └── templates/
│   │       ├── executive_report.html
│   │       └── technical_report.html
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── logging.py
│   │   └── security.py
│   └── utils/
│       ├── hash_utils.py
│       ├── ioc_extractor.py
│       └── mutation_runner.py
├── rules/
│   ├── yara/
│   │   ├── banking_trojans.yar
│   │   ├── generic_malware.yar
│   │   └── auto_generated/     # feedback loop output
│   ├── semgrep/
│   │   └── banking_malware.yml
│   └── attck_mapping.json
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── fixtures/
│   │   └── sample_apks/        # safe test samples
│   └── e2e/
├── frontend/                   # React UI
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── deploy/
│   ├── helm/                   # K8s Helm charts
│   ├── terraform/              # IaC (optional)
│   └── ansible/                # On-prem deployment
├── docs/
│   ├── architecture/
│   ├── api/
│   └── runbooks/
└── scripts/
    ├── setup_dev.sh
    ├── seed_test_data.py
    └── benchmark.py
```

---

## 15. Tool Selection Rationale (Summary Table)

| Choice | Over Alternative | Why |
|---|---|---|
| **Ollama** for LLM serving | vLLM, TGI | Simpler ops, model management, single binary |
| **Neo4j** for primary graph | JanusGraph, ArangoDB | Best Cypher, Graph Data Science library, mature |
| **Qdrant** for vector search | Milvus, Weaviate, pgvector | Easier to operate, fast, great Python client |
| **LangGraph** for orchestration | AutoGen, CrewAI alone | Stateful, supports cycles, production-grade |
| **DSPy** for prompts | Raw prompting | Compiled, optimizable, less hallucination |
| **Frida** over Xposed | Xposed | Modern, no root, JS scripting, broader API |
| **andrograud** for parsing | AAPT2 alone | Python-native, more complete analysis |
| **Phi-3 Mini** for triage | Llama-3.2-1B | Better at structured tasks, still tiny |
| **DeepSeek-Coder-V2** for code | CodeLlama, StarCoder | State-of-art open code LLM |
| **mitmproxy** over Wireshark | Wireshark | Scriptable, Python API, full automation |
| **PostgreSQL** for metadata | MySQL, MongoDB | JSONB for flexible IOCs, mature, great Python |
| **React + Vite** over Next.js | Next.js | Lighter, no SSR needed, faster dev |

---

## 16. Security Hardening Checklist (Per Tool)

| Tool | Hardening |
|---|---|
| Neo4j | Auth required, HTTPS only, no anonymous browser access in prod |
| MinIO | TLS, IAM policies, server-side encryption |
| PostgreSQL | TLS, row-level security for multi-tenant future |
| Redis | AUTH, no internet exposure, separate cluster per env |
| Ollama | Network bind to internal only, no public exposure |
| Grafana | LDAP/SSO integration, RBAC |
| All | Secrets via Vault, never env vars in code |

---

## 17. Testing Tooling

| Tool | Purpose |
|---|---|
| pytest | Unit + integration tests |
| pytest-asyncio | Async test support |
| pytest-cov | Coverage |
| Locust | Load testing (concurrent APK submissions) |
| Hypothesis | Property-based testing for analysis modules |
| OWASP ZAP | Web API security scanning |
| Bandit | Python security linting |
| Trivy | Container image vulnerability scanning |
| Gitleaks | Secret leak prevention |
| pre-commit | Run all checks before commit |

---

*Next: See `04_IMPLEMENTATION_PHASES.md` for the phase-by-phase build plan with tasks, files, and acceptance criteria.*
