# PARALLAX — Phase-wise Implementation Plan
## From Zero to Flagship: Complete Build Roadmap

---

## 0. How to Use This Document

Each phase is a **2-3 week build block** with:
- **Objectives** — what you accomplish
- **Deliverables** — concrete outputs
- **Tasks** — numbered, file paths, code structures
- **Acceptance Criteria** — how you know it works
- **Dependencies** — what must exist first

Each task is bite-sized (2-5 minutes of focused work following TDD).

**Total timeline: 20 weeks (5 months) to flagship-grade MVP.**

---

## Phase 0 — Foundation (Week 1-2)

### Objectives
Establish project structure, dev environment, CI/CD, and base infrastructure that every later phase depends on.

### Deliverables
- Working Docker Compose stack with all infra services
- FastAPI skeleton with health checks
- PostgreSQL schema initialized
- CI pipeline green
- Documentation scaffold

### Tasks

#### Task 0.1 — Repository Setup
**Files:**
- Create: `parallax/.gitignore`
- Create: `parallax/README.md`
- Create: `parallax/pyproject.toml`
- Create: `parallax/requirements.txt`
- Create: `parallax/.env.example`

**Step 1:** Initialize git repo with `.gitignore` (Python, Node, IDE, secrets)
**Step 2:** Create README with project name, description, quickstart
**Step 3:** Create `pyproject.toml` with project metadata
**Step 4:** Copy requirements from `03_TECH_STACK.md`
**Step 5:** Create `.env.example` with all required env vars (no secrets)

**Acceptance:** `git clone`, `cd`, `pip install -r requirements.txt` works.

---

#### Task 0.2 — Docker Compose Infrastructure
**Files:**
- Create: `parallax/docker-compose.yml`
- Create: `parallax/prometheus.yml`
- Create: `parallax/.env` (local only, gitignored)

**Step 1:** Compose file with: redis, postgres, minio, neo4j, qdrant, ollama, grafana, jaeger, prometheus
**Step 2:** Health checks for each service
**Step 3:** Volume mounts for persistence
**Step 4:** Network isolation (separate analysis network)
**Step 5:** Test: `docker compose up -d` brings all up, `docker compose ps` shows healthy

**Acceptance:** All 9 services running, no errors, ports accessible.

---

#### Task 0.3 — FastAPI Skeleton
**Files:**
- Create: `parallax/parallax/__init__.py`
- Create: `parallax/parallax/api/__init__.py`
- Create: `parallax/parallax/api/main.py`
- Create: `parallax/parallax/core/__init__.py`
- Create: `parallax/parallax/core/config.py`
- Create: `parallax/parallax/core/logging.py`

**Step 1:** `core/config.py` using `pydantic-settings` for env loading
**Step 2:** `core/logging.py` using `structlog` for structured JSON logs
**Step 3:** `api/main.py` FastAPI app with:
  - `/health` endpoint
  - `/ready` endpoint (checks all infra connections)
  - OpenAPI docs at `/docs`
  - CORS middleware
  - OpenTelemetry instrumentation

**Step 4:** Test: `uvicorn parallax.api.main:app --reload`, hit `/health` returns 200

**Acceptance:** API runs, /docs accessible, all health checks pass.

---

#### Task 0.4 — Database Initialization
**Files:**
- Create: `parallax/parallax/core/database.py`
- Create: `parallax/migrations/env.py`
- Create: `parallax/migrations/versions/0001_initial.py`

**Step 1:** SQLAlchemy async engine in `core/database.py`
**Step 2:** Alembic for migrations
**Step 3:** Initial migration with `analyses`, `iocs`, `audit_log` tables
**Step 4:** Test: `alembic upgrade head` succeeds, tables exist in PostgreSQL

**Acceptance:** Schema applied, can query tables via SQLAlchemy session.

---

#### Task 0.5 — CI Pipeline
**Files:**
- Create: `parallax/.github/workflows/ci.yml`
- Create: `parallax/.pre-commit-config.yaml`
- Create: `parallax/pytest.ini`

**Step 1:** GitHub Actions workflow:
  - Lint (ruff)
  - Type check (mypy)
  - Unit tests (pytest)
  - Security scan (bandit, gitleaks)
  - Container scan (trivy)
**Step 2:** pre-commit hooks (ruff, mypy, gitleaks)
**Step 3:** Push to GitHub, verify pipeline runs green

**Acceptance:** Every PR triggers CI; all checks pass.

---

#### Task 0.6 — Documentation Scaffold
**Files:**
- Create: `parallax/docs/README.md`
- Create: `parallax/docs/architecture/`
- Create: `parallax/docs/api/`
- Create: `parallax/docs/runbooks/`

**Step 1:** Create `docs/` tree
**Step 2:** Copy all PSBs files to `docs/architecture/`
**Step 3:** Create `CONTRIBUTING.md` (TDD workflow, commit conventions)

**Acceptance:** New developer can onboard from docs alone.

---

### Phase 0 Acceptance Criteria
- [ ] `git clone && docker compose up -d && pip install -r requirements.txt && uvicorn parallax.api.main:app` → API runs
- [ ] All infrastructure services healthy
- [ ] CI green on first commit
- [ ] Database schema applied
- [ ] Documentation complete

---

## Phase 1 — Ingestion & Triage (Week 3-4)

### Objectives
Accept APK submissions, perform fast pre-screening, queue for analysis.

### Deliverables
- APK upload REST endpoint
- Triage LLM integration (Phi-3 Mini)
- MinIO storage for originals
- Celery task queue with priorities
- Status query endpoint

### Tasks

#### Task 1.1 — Submission Model
**Files:**
- Create: `parallax/parallax/api/schemas/submission.py`
- Create: `parallax/parallax/core/models/submission.py`

**Step 1:** Pydantic schema for submission
**Step 2:** SQLAlchemy model
**Step 3:** Test: Create submission, retrieve from DB

---

#### Task 1.2 — APK Upload Endpoint
**Files:**
- Create: `parallax/parallax/api/routes/analyze.py`
- Create: `parallax/parallax/api/routes/status.py`
- Modify: `parallax/parallax/api/main.py`

**Step 1:** POST `/api/v1/analyze` with multipart file upload
**Step 2:** Compute SHA256, MD5, file size
**Step 3:** Store original in MinIO at `s3://parallax-apks/{sha256}.apk`
**Step 4:** Create `submissions` record in DB
**Step 5:** Enqueue triage task
**Step 6:** Return submission_id

**Step 7:** Test: Upload sample APK, verify record created, file in MinIO

---

#### Task 1.3 — APKiD Integration
**Files:**
- Create: `parallax/parallax/analysis/ingestion/apkid_runner.py`
- Create: `parallax/tests/unit/test_apkid_runner.py`

**Step 1:** TDD — write test that calls APKiD on sample APK
**Step 2:** Implement wrapper using `apkid` Python library
**Step 3:** Returns: packer, anti-VM, anti-debug, compiler
**Step 4:** Test passes

**Acceptance:** APKiD runs in <5 seconds, output captured to DB.

---

#### Task 1.4 — ssdeep Integration
**Files:**
- Create: `parallax/parallax/analysis/ingestion/ssdeep_runner.py`
- Create: `parallax/tests/unit/test_ssdeep_runner.py`

**Step 1:** TDD test
**Step 2:** Implement wrapper
**Step 3:** Store hash, query against historical hashes
**Step 4:** If > 90% match to known-malicious, fast-path

**Acceptance:** Fuzzy hash generated, similarity check works.

---

#### Task 1.5 — Ollama + Phi-3 Mini Setup
**Files:**
- Create: `parallax/parallax/ai/ollama_client.py`
- Create: `parallax/parallax/ai/agents/triage.py`
- Create: `parallax/tests/unit/test_triage.py`

**Step 1:** Docker `ollama` running, `ollama pull phi3:mini`
**Step 2:** `ollama_client.py` — async wrapper for Ollama API
**Step 3:** Triage agent prompt (see `07_AGENT_PROMPTS.md`)
**Step 4:** Test: Triage returns valid JSON for sample APK manifest

**Acceptance:** Phi-3 Mini returns pre-score in <2 seconds.

---

#### Task 1.6 — Celery Task Queue
**Files:**
- Create: `parallax/parallax/workers/__init__.py`
- Create: `parallax/parallax/workers/celery_app.py`
- Create: `parallax/parallax/workers/triage_worker.py`

**Step 1:** Celery app with Redis broker
**Step 2:** Priority queues: `critical`, `high`, `normal`, `low`
**Step 3:** Triage task: APKiD + ssdeep + Phi-3 triage
**Step 4:** Update submission status at each step
**Step 5:** Test: Submit APK, watch task execute, status updates visible

**Acceptance:** Tasks execute, status updates work, priority routing functional.

---

#### Task 1.7 — Status & History Endpoints
**Files:**
- Create: `parallax/parallax/api/routes/history.py`
- Modify: `parallax/parallax/api/main.py`

**Step 1:** GET `/api/v1/analysis/{id}` → status, progress, current stage
**Step 2:** GET `/api/v1/history` → paginated list of past analyses
**Step 3:** Test: Submit 3 APKs, query history, verify pagination

**Acceptance:** Status endpoint accurate, history queryable.

---

### Phase 1 Acceptance Criteria
- [ ] APK upload works, returns submission_id
- [ ] APKiD, ssdeep, Phi-3 triage all run automatically
- [ ] Triage score visible in DB within 5 seconds
- [ ] CRITICAL priority APKs jump queue
- [ ] Status endpoint shows real-time progress
- [ ] Original APK stored in MinIO, retrievable

---

## Phase 2 — Static Analysis Pipeline (Week 5-7)

### Objectives
Deep static analysis of APK code, resources, manifest, and binaries.

### Deliverables
- androguard integration
- jadx decompilation
- FlowDroid taint analysis
- YARA rule engine
- Semgrep custom rules
- NetworkX permission graph
- Binary similarity (Diaphora)
- Static analysis worker in Celery

### Tasks

#### Task 2.1 — androguard Integration
**Files:**
- Create: `parallax/parallax/analysis/static/androguard_runner.py`
- Create: `parallax/parallax/analysis/static/extractors.py`
- Create: `parallax/tests/unit/test_androguard.py`

**Step 1:** TDD test extracting permissions
**Step 2:** Implement permission extraction
**Step 3:** Test extracting components (activities, services, receivers)
**Step 4:** Implement
**Step 5:** Test extracting API calls (class.method references in DEX)
**Step 6:** Implement
**Step 7:** Test extracting hardcoded strings (URLs, IPs)
**Step 8:** Implement with regex patterns

**Acceptance:** All extractors return structured JSON, all tests pass.

---

#### Task 2.2 — jadx Decompilation Pipeline
**Files:**
- Create: `parallax/parallax/analysis/static/jadx_runner.py`
- Create: `parallax/parallax/analysis/static/code_preprocessor.py`

**Step 1:** Shell out to jadx CLI
**Step 2:** Output to MinIO: `s3://parallax-decompiled/{sha256}/`
**Step 3:** Pre-process: split large files, filter framework code
**Step 4:** Output: structured "code chunks" ready for LLM consumption
**Step 5:** Test: Decompile sample APK, verify Java files present

**Acceptance:** Decompiled Java stored, code chunks ready for analysis.

---

#### Task 2.3 — NetworkX Permission Graph
**Files:**
- Create: `parallax/parallax/analysis/static/permission_graph.py`
- Create: `parallax/tests/unit/test_permission_graph.py`

**Step 1:** Build graph: APK → permissions → APIs → sinks
**Step 2:** Compute centrality metrics
**Step 3:** Identify dangerous permission clusters
**Step 4:** Risk score per cluster
**Step 5:** Test: Sample APK produces meaningful graph

**Acceptance:** Graph construction <1 minute, centrality scores computed.

---

#### Task 2.4 — YARA Rule Engine
**Files:**
- Create: `parallax/parallax/analysis/static/yara_runner.py`
- Create: `parallax/rules/yara/banking_trojans.yar` (curated)
- Create: `parallax/parallax/analysis/static/auto_yara.py`
- Create: `parallax/tests/unit/test_yara.py`

**Step 1:** yara-python wrapper, compile rule directory
**Step 2:** Scan DEX files against rules
**Step 3:** Return matches with offsets
**Step 4:** Auto-generate YARA rules from observed patterns (feedback loop)
**Step 5:** Test: Known-bad APK triggers known rules

**Acceptance:** YARA matches detected, results structured.

---

#### Task 2.5 — Semgrep Custom Rules
**Files:**
- Create: `parallax/rules/semgrep/banking_malware.yml`
- Create: `parallax/parallax/analysis/static/semgrep_runner.py`
- Create: `parallax/tests/unit/test_semgrep.py`

**Step 1:** Author rules:
  - SMS interception patterns
  - Accessibility service abuse
  - Overlay attack patterns
  - Keylogger signatures
  - Crypto API misuse

**Step 2:** Run on decompiled Java
**Step 3:** Return matches with file, line, severity
**Step 4:** Test: Sample APK with SMS interception triggers rule

**Acceptance:** Custom rules fire on known patterns.

---

#### Task 2.6 — FlowDroid Taint Analysis
**Files:**
- Create: `parallax/parallax/analysis/static/flowdroid_runner.py`
- Create: `parallax/tests/integration/test_flowdroid.py`

**Step 1:** Shell out to FlowDroid JAR
**Step 2:** Parse output: taint flows
**Step 3:** Map to risk: source (user input) → sink (network)
**Step 4:** Test: APK known to exfiltrate SMS content shows taint flow

**Acceptance:** Taint flows extracted, risks assigned.

---

#### Task 2.7 — Binary Similarity (Diaphora)
**Files:**
- Create: `parallax/parallax/analysis/static/binary_diff.py`
- Create: `parallax/tests/integration/test_binary_diff.py`

**Step 1:** Extract native libs from APK
**Step 2:** Run Diaphora against all historical samples
**Step 3:** Return similarity scores
**Step 4:** Test: Sample APK compared against itself returns ~1.0

**Acceptance:** Similarity search works, results in <5 minutes.

---

#### Task 2.8 — Static Analysis Worker
**Files:**
- Create: `parallax/parallax/workers/static_worker.py`
- Create: `parallax/parallax/analysis/static/aggregator.py`

**Step 1:** Celery task `run_static_analysis(submission_id)`
**Step 2:** Orchestrates all 7 static tools
**Step 3:** Aggregates outputs into unified `static_analysis.json`
**Step 4:** Stores in PostgreSQL + S3
**Step 5:** Updates status at each step
**Step 6:** Test: Full static analysis on sample APK in <5 minutes

**Acceptance:** Complete static analysis pipeline functional.

---

### Phase 2 Acceptance Criteria
- [ ] All 7 static analysis tools integrated
- [ ] Analysis completes in <5 minutes
- [ ] Unified JSON output stored
- [ ] YARA auto-generation working
- [ ] Permission graph produced
- [ ] Binary similarity returns meaningful results
- [ ] All tests green

---

## Phase 3 — Dynamic Analysis Pipeline (Week 8-10)

### Objectives
Runtime analysis: instrumented Android emulator with full traffic capture, behavior observation, mutation testing.

### Deliverables
- Android AVD orchestration
- Frida hook library
- DroidBot-GPT UI automation
- mitmproxy traffic capture
- Mutation testing framework
- Screenshot capture pipeline

### Tasks

#### Task 3.1 — AVD Orchestration
**Files:**
- Create: `parallax/parallax/analysis/dynamic/avd_manager.py`
- Create: `parallax/parallax/analysis/dynamic/install.py`
- Create: `parallax/tests/integration/test_avd.py`

**Step 1:** `avdmanager create avd` with x86_64 image
**Step 2:** Headless boot with `-no-window -no-audio`
**Step 3:** Wait for boot complete
**Step 4:** Install APK
**Step 5:** Install Frida server, mitmproxy CA
**Step 6:** Test: Install sample APK, launch

**Acceptance:** AVD boots headless, APK installs in <2 minutes.

---

#### Task 3.2 — Frida Hook Library
**Files:**
- Create: `parallax/parallax/analysis/dynamic/frida_hooks/sms_interception.js`
- Create: `parallax/parallax/analysis/dynamic/frida_hooks/accessibility_abuse.js`
- Create: `parallax/parallax/analysis/dynamic/frida_hooks/keylogger.js`
- Create: `parallax/parallax/analysis/dynamic/frida_hooks/crypto_extraction.js`
- Create: `parallax/parallax/analysis/dynamic/frida_hooks/network_logger.js`
- Create: `parallax/parallax/analysis/dynamic/frida_runner.py`
- Create: `parallax/tests/integration/test_frida.py`

**Step 1:** Author hook scripts for each behavior
**Step 2:** Python runner that injects all hooks
**Step 3:** Collects hook firings to JSON stream
**Step 4:** Test: Hooks fire on known-bad APK

**Acceptance:** All hooks fire correctly, events captured.

---

#### Task 3.3 — DroidBot-GPT UI Automation
**Files:**
- Create: `parallax/parallax/analysis/dynamic/droidbot_gpt.py`
- Create: `parallax/parallax/analysis/dynamic/prompts/droidbot.py`

**Step 1:** Wrap DroidBot (or implement LLM-driven UI explorer)
**Step 2:** Send UI state to LLM, get next action
**Step 3:** Execute action, observe result, repeat
**Step 4:** Capture all transitions
**Step 5:** Test: LLM navigates 3-screen app successfully

**Acceptance:** Automated UI exploration covers 80%+ of reachable screens.

---

#### Task 3.4 — mitmproxy Traffic Capture
**Files:**
- Create: `parallax/parallax/analysis/dynamic/traffic_capture.py`
- Create: `parallax/parallax/analysis/dynamic/protocol_decoders.py`

**Step 1:** Start mitmdump in background
**Step 2:** Configure AVD to use as proxy
**Step 3:** Capture all HTTP/HTTPS
**Step 4:** Custom decoders for non-HTTP protocols (Scapy)
**Step 5:** Extract: destinations, payloads, encryption indicators
**Step 6:** Test: Captured traffic matches expected C2

**Acceptance:** Full traffic capture, decoded and structured.

---

#### Task 3.5 — System Call Monitoring
**Files:**
- Create: `parallax/parallax/analysis/dynamic/strace_runner.py`

**Step 1:** Wrap APK launch in strace
**Step 2:** Capture syscalls to file
**Step 3:** Parse for: file ops, process spawns, IPC, network
**Step 4:** Flag suspicious patterns (writing to /system, spawning shell)
**Step 5:** Test: Known rootkit behavior detected

**Acceptance:** Syscall analysis produces structured output.

---

#### Task 3.6 — Screenshot Capture Pipeline
**Files:**
- Create: `parallax/parallax/analysis/dynamic/screenshot.py`

**Step 1:** Capture every screen state (UI change detection)
**Step 2:** Store in MinIO with metadata
**Step 3:** Index for visual AI consumption
**Step 4:** Test: 50+ screenshots captured for sample run

**Acceptance:** Complete visual record of app run.

---

#### Task 3.7 — Mutation Testing Framework
**Files:**
- Create: `parallax/parallax/analysis/dynamic/mutation_runner.py`
- Create: `parallax/parallax/analysis/dynamic/mutations.py`

**Step 1:** Define mutations: locale, SIM prefix, time, installed apps
**Step 2:** Re-run APK with each mutation
**Step 3:** Compare behavior across runs
**Step 4:** Flag behavior changes as suspicious
**Step 5:** Test: Locale change triggers hidden C2 in sample

**Acceptance:** Context-aware behavior detected.

---

#### Task 3.8 — Dynamic Analysis Worker
**Files:**
- Create: `parallax/parallax/workers/dynamic_worker.py`
- Create: `parallax/parallax/analysis/dynamic/aggregator.py`

**Step 1:** Celery task `run_dynamic_analysis(submission_id)`
**Step 2:** Orchestrates all dynamic components
**Step 3:** Aggregates events into timeline
**Step 4:** Stores in PostgreSQL
**Step 5:** Test: Full dynamic analysis in <10 minutes

**Acceptance:** Complete dynamic analysis pipeline.

---

### Phase 3 Acceptance Criteria
- [ ] AVD boots, APK installs, runs
- [ ] All Frida hooks fire correctly
- [ ] DroidBot-GPT explores UI
- [ ] Full traffic captured and decoded
- [ ] Screenshots captured
- [ ] Mutation testing reveals context-aware behavior
- [ ] Complete analysis in <10 minutes

---

## Phase 4 — AI Reasoning Cortex (Week 11-13)

### Objectives
The intelligence layer: 5 specialized AI agents with debate protocol, grounded in real tool outputs.

### Deliverables
- Code Interpreter agent (DeepSeek-Coder-V2)
- Behavior Analyst agent (Mistral-Large)
- Intel Correlator agent (RAG over MITRE ATT&CK)
- Visual Intelligence agent (LLaVA)
- Debate Layer
- Synthesis agent
- LangGraph orchestration

### Tasks

#### Task 4.1 — Ollama Production Setup
**Files:**
- Create: `parallax/parallax/ai/ollama_pool.py`
- Create: `parallax/scripts/pull_models.sh`

**Step 1:** Pre-pull all required models
**Step 2:** Model pool management (avoid contention)
**Step 3:** Fallback logic if model unavailable
**Step 4:** Test: All models respond correctly

**Acceptance:** Model pool serves 5+ concurrent requests.

---

#### Task 4.2 — Code Interpreter Agent
**Files:**
- Create: `parallax/parallax/ai/agents/code_interpreter.py`
- Create: `parallax/parallax/ai/prompts/code_interpreter.py`
- Create: `parallax/parallax/ai/schemas.py`
- Create: `parallax/tests/unit/test_code_interpreter.py`

**Step 1:** DSPy signature: decompiled_code → intent_classification
**Step 2:** Few-shot examples from known banking trojans
**Step 3:** Output schema: intent, risk, evidence, attck_techniques
**Step 4:** DSPy optimization on labeled set
**Step 5:** Test: Known-bad code returns correct intent

**Acceptance:** Agent accurately classifies known malware code.

---

#### Task 4.3 — Behavior Analyst Agent
**Files:**
- Create: `parallax/parallax/ai/agents/behavior_analyst.py`
- Create: `parallax/parallax/ai/prompts/behavior_analyst.py`
- Create: `parallax/tests/unit/test_behavior_analyst.py`

**Step 1:** Input: runtime event stream
**Step 2:** Output: narrative + risk per phase
**Step 3:** Maps to kill chain stages
**Step 4:** Test: Known attack sequence produces correct narrative

**Acceptance:** Behavior narrative matches ground truth.

---

#### Task 4.4 — Intel Correlator + RAG
**Files:**
- Create: `parallax/parallax/ai/agents/intel_correlator.py`
- Create: `parallax/parallax/ai/rag/attck_ingest.py`
- Create: `parallax/parallax/ai/rag/misp_query.py`
- Create: `parallax/tests/integration/test_intel_correlator.py`

**Step 1:** Ingest MITRE ATT&CK Mobile XML into LlamaIndex
**Step 2:** Ingest MISP events
**Step 3:** Ingest past PARALLAX analyses
**Step 4:** RAG pipeline: IOCs → relevant context → LLM mapping
**Step 5:** Test: Known IOC returns correct campaign attribution

**Acceptance:** ATT&CK mapping + attribution with confidence scores.

---

#### Task 4.5 — Visual Intelligence Agent
**Files:**
- Create: `parallax/parallax/ai/agents/visual.py`
- Create: `parallax/parallax/ai/prompts/visual.py`
- Create: `parallax/tests/integration/test_visual.py`

**Step 1:** For each screenshot, query LLaVA
**Step 2:** Brand impersonation scoring via multimodal embedding
**Step 3:** Overlay attack detection
**Step 4:** Test: Known phishing UI detected with high confidence

**Acceptance:** Phishing UI detected, brand similarity scored.

---

#### Task 4.6 — Debate Layer
**Files:**
- Create: `parallax/parallax/ai/debate_layer.py`
- Create: `parallax/tests/unit/test_debate.py`

**Step 1:** Implement contradiction detection logic
**Step 2:** Score adjustment for contradictions (evasion signature)
**Step 3:** Surface contradictions as alerts
**Step 4:** Test: Static clean + dynamic dirty → high alert

**Acceptance:** Debate logic correctly handles all agreement patterns.

---

#### Task 4.7 — Synthesis Agent
**Files:**
- Create: `parallax/parallax/ai/agents/synthesis.py`
- Create: `parallax/parallax/ai/risk_scoring.py`
- Create: `parallax/parallax/ai/prompts/synthesis.py`
- Create: `parallax/tests/integration/test_synthesis.py`

**Step 1:** Inputs: all 5 agent outputs + debate result
**Step 2:** Final risk score (explainable, weighted)
**Step 3:** Verdict + confidence interval
**Step 4:** Report generation (executive + technical)
**Step 5:** Test: Known-bad APK returns CRITICAL verdict

**Acceptance:** Synthesis produces complete verdict + report.

---

#### Task 4.8 — LangGraph Orchestration
**Files:**
- Create: `parallax/parallax/ai/orchestration.py`
- Create: `parallax/tests/integration/test_orchestration.py`

**Step 1:** Define agent graph:
```
INPUT → [parallel: code_interp, behavior, intel, visual] → debate → synthesis → OUTPUT
```
**Step 2:** State management
**Step 3:** Error handling per node
**Step 4:** Test: Full pipeline on sample APK

**Acceptance:** Orchestration runs end-to-end in <2 minutes.

---

### Phase 4 Acceptance Criteria
- [ ] All 5 agents operational
- [ ] Debate layer handles contradictions
- [ ] Synthesis produces verdict + report
- [ ] Full cortex runs in <2 minutes
- [ ] DSPy-optimized prompts (not hand-tuned)
- [ ] All agents grounded in real tool outputs

---

## Phase 5 — TAIG Knowledge Graph (Week 14-15)

### Objectives
Build the living knowledge graph — every APK enriches it.

### Deliverables
- Neo4j schema fully populated
- Qdrant vector index operational
- Graph population pipelines
- Threat-hunting API endpoints
- MISP sync

### Tasks

#### Task 5.1 — Neo4j Schema Initialization
**Files:**
- Create: `parallax/parallax/knowledge/neo4j_client.py`
- Create: `parallax/parallax/knowledge/schema.py`
- Create: `parallax/parallax/knowledge/migrations/001_initial.cypher`

**Step 1:** Define constraints (unique sha256, etc.)
**Step 2:** Define indexes (for fast queries)
**Step 3:** Bootstrap script
**Step 4:** Test: Schema applied, constraints work

**Acceptance:** Graph ready for population.

---

#### Task 5.2 — Graph Population Pipeline
**Files:**
- Create: `parallax/parallax/knowledge/population.py`
- Create: `parallax/tests/integration/test_population.py`

**Step 1:** For each analyzed APK:
  - Create APK node
  - MERGE all IOCs (IP, domain, permission, etc.)
  - Create all relationships
  - Compute derived metrics
**Step 2:** Test: Sample APK creates full subgraph

**Acceptance:** Population idempotent, handles updates.

---

#### Task 5.3 — Binary Similarity Edge Creation
**Files:**
- Create: `parallax/parallax/knowledge/similarity_edges.py`

**Step 1:** After analysis, run Diaphora against all historical APKs
**Step 2:** Create SHARES_CODE_WITH edges where similarity > 0.5
**Step 3:** Test: New APK finds similar prior samples

**Acceptance:** Cross-APK similarity queries return results.

---

#### Task 5.4 — Campaign Detection Algorithm
**Files:**
- Create: `parallax/parallax/knowledge/campaign_detection.py`

**Step 1:** Community detection (Louvain) over APK graph
**Step 2:** Cluster APKs into campaigns
**Step 3:** Create Campaign nodes + PART_OF edges
**Step 4:** Test: Known campaign correctly clustered

**Acceptance:** Campaign detection produces meaningful clusters.

---

#### Task 5.5 — Qdrant Vector Index
**Files:**
- Create: `parallax/parallax/knowledge/qdrant_client.py`
- Create: `parallax/parallax/knowledge/embeddings.py`

**Step 1:** Generate embeddings (code intent + screenshot)
**Step 2:** Index per submission
**Step 3:** Similarity search API
**Step 4:** Test: Similar APK query returns top-k matches

**Acceptance:** Vector search accurate + fast (<500ms).

---

#### Task 5.6 — Threat Hunting API
**Files:**
- Create: `parallax/parallax/api/routes/graph.py`
- Create: `parallax/parallax/api/routes/hunt.py`

**Step 1:** POST `/api/v1/graph/cypher` → execute Cypher
**Step 2:** POST `/api/v1/graph/similar` → vector similarity
**Step 3:** POST `/api/v1/hunt` → structured threat hunt
**Step 4:** Test: Hunt query returns expected matches

**Acceptance:** Threat hunting API functional.

---

#### Task 5.7 — MISP Sync
**Files:**
- Create: `parallax/parallax/knowledge/misp_sync.py`

**Step 1:** Push IOCs to MISP after each analysis
**Step 2:** Pull MISP events for intel correlator
**Step 3:** STIX 2.1 format
**Step 4:** Test: IOCs visible in MISP UI

**Acceptance:** Bidirectional MISP sync works.

---

### Phase 5 Acceptance Criteria
- [ ] Neo4j + Qdrant populated automatically
- [ ] Similarity queries work
- [ ] Campaign detection runs
- [ ] Threat hunting API functional
- [ ] MISP sync bidirectional
- [ ] Cross-APK intelligence demonstrable

---

## Phase 6 — Delivery Layer (Week 16-17)

### Objectives
Turn analysis into actionable intelligence and deliver to right people.

### Deliverables
- PDF report generation
- STIX 2.1 export
- Auto-generated YARA rules
- Suricata rules
- Webhook dispatchers
- Grafana dashboards
- Fraud rule recommendations

### Tasks

#### Task 6.1 — Report Generation
**Files:**
- Create: `parallax/parallax/delivery/report_generator.py`
- Create: `parallax/parallax/delivery/templates/executive.html`
- Create: `parallax/parallax/delivery/templates/technical.html`
- Create: `parallax/tests/unit/test_report_generator.py`

**Step 1:** Jinja2 templates for executive + technical
**Step 2:** WeasyPrint for PDF rendering
**Step 3:** Embed screenshots, ATT&CK heatmap
**Step 4:** Test: PDF generated, valid, <2MB

**Acceptance:** Reports generated, professional quality.

---

#### Task 6.2 — STIX 2.1 Export
**Files:**
- Create: `parallax/parallax/delivery/stix_exporter.py`
- Create: `parallax/tests/unit/test_stix.py`

**Step 1:** Map PARALLAX entities to STIX 2.1 objects
**Step 2:** Bundle per analysis
**Step 3:** Test: STIX bundle valid, imports into MISP/OpenCTI

**Acceptance:** STIX 2.1 bundles valid + portable.

---

#### Task 6.3 — YARA Auto-Generation
**Files:**
- Create: `parallax/parallax/delivery/yara_generator.py`

**Step 1:** Extract unique byte patterns from APK
**Step 2:** Generate YARA rule with extracted strings
**Step 3:** Test rule against known samples (FP check)
**Step 4:** Save to `rules/yara/auto_generated/`
**Step 5:** Test: New YARA rule catches the original sample

**Acceptance:** Auto-generated YARA rules work.

---

#### Task 6.4 — Webhook System
**Files:**
- Create: `parallax/parallax/delivery/webhook_dispatcher.py`
- Create: `parallax/parallax/api/routes/webhooks.py`

**Step 1:** Webhook configuration per bank integration
**Step 2:** Fire on: high-risk verdict, new campaign, attribution match
**Step 3:** Retry logic, signing
**Step 4:** Test: Webhook delivered, payload valid

**Acceptance:** Webhooks reliable, signed, retried.

---

#### Task 6.5 — Grafana Dashboards
**Files:**
- Create: `parallax/parallax/delivery/grafana_setup.py`
- Create: `parallax/parallax/delivery/dashboards/threat_overview.json`
- Create: `parallax/parallax/delivery/dashboards/campaign_tracker.json`

**Step 1:** Auto-provision Grafana data source
**Step 2:** Pre-built dashboards
**Step 3:** Test: Dashboards render, data flows

**Acceptance:** Live dashboards accessible.

---

#### Task 6.6 — Fraud Rule Recommendations
**Files:**
- Create: `parallax/parallax/delivery/fraud_rules.py`

**Step 1:** Generate DSL rules from ATT&CK techniques observed
**Step 2:** Example: "Block transactions from device where accessibility service is active + app X installed"
**Step 3:** Format per bank's rule engine (configurable)
**Step 4:** Test: Rules parseable, actionable

**Acceptance:** Fraud rules generated, actionable.

---

#### Task 6.7 — ATT&CK Navigator Export
**Files:**
- Create: `parallax/parallax/delivery/attck_navigator.py`

**Step 1:** Generate ATT&CK Navigator layer JSON
**Step 2:** Color-code by technique confidence
**Step 3:** Test: Imports into Navigator correctly

**Acceptance:** Navigator layers importable.

---

### Phase 6 Acceptance Criteria
- [ ] PDF reports generated
- [ ] STIX 2.1 valid
- [ ] YARA rules auto-generated
- [ ] Webhooks delivered
- [ ] Dashboards live
- [ ] Fraud rules actionable
- [ ] ATT&CK Navigator layers importable

---

## Phase 7 — Integration & Hardening (Week 18-20)

### Objectives
End-to-end testing, performance, security, documentation, pilot readiness.

### Tasks

#### Task 7.1 — End-to-End Integration Tests
**Files:**
- Create: `parallax/tests/e2e/test_full_pipeline.py`
- Create: `parallax/tests/fixtures/sample_apks/`

**Step 1:** Curate 20 sample APKs (known-bad, suspicious, benign)
**Step 2:** Run full pipeline on each
**Step 3:** Verify: triage → static → dynamic → visual → cortex → TAIG → delivery
**Step 4:** Verify reports, IOCs, graph nodes all created

**Acceptance:** Full pipeline works for all sample types.

---

#### Task 7.2 — Performance Benchmarking
**Files:**
- Create: `parallax/scripts/benchmark.py`

**Step 1:** Measure: time per stage, end-to-end latency
**Step 2:** Throughput: APKs/hour under load
**Step 3:** Concurrent submissions (Locust)
**Step 4:** Identify bottlenecks

**Acceptance:** <12 minutes per APK, 50+ APKs/hour with scale.

---

#### Task 7.3 — Security Hardening
**Files:**
- Various

**Step 1:** Network isolation validation
**Step 2:** Container image scanning
**Step 3:** Secrets management
**Step 4:** SSL/TLS everywhere
**Step 5:** RBAC for UI

**Acceptance:** Penetration test passes.

---

#### Task 7.4 — Documentation
**Files:**
- Create: `parallax/docs/runbooks/`
- Create: `parallax/docs/operations/`
- Create: `parallax/docs/troubleshooting.md`

**Step 1:** Operations runbook (start/stop, scaling)
**Step 2:** Troubleshooting guide
**Step 3:** Disaster recovery
**Step 4:** Backup procedures (Neo4j, MinIO)

**Acceptance:** Ops team can run system from docs.

---

#### Task 7.5 — Pilot Deployment
**Files:**
- Create: `parallax/deploy/helm/parallax/`
- Create: `parallax/deploy/terraform/`

**Step 1:** Helm charts for K8s
**Step 2:** Terraform for cloud provisioning
**Step 3:** Pilot environment stood up
**Step 4:** First 100 real APKs processed

**Acceptance:** System runs in pilot, analyst feedback positive.

---

### Phase 7 Acceptance Criteria
- [ ] E2E tests green
- [ ] Performance meets targets
- [ ] Security hardened
- [ ] Documentation complete
- [ ] Pilot deployed, first 100 APKs processed successfully
- [ ] System measurably smarter (better YARA matches, attribution accuracy over time)

---

## Cross-Phase Concerns

### Continuous Testing
- TDD throughout (red-green-refactor)
- Unit tests per module
- Integration tests for cross-module
- E2E tests for full pipeline
- Coverage target: >80%

### Continuous Documentation
- Update docs with each phase
- API docs auto-generated (OpenAPI)
- ADRs (Architecture Decision Records) for major choices

### Continuous Security
- Pre-commit security scans
- Container image scans in CI
- Quarterly penetration testing
- Bug bounty program (post-pilot)

### Continuous Performance
- Profiling in dev
- Load testing each phase
- Latency budgets enforced
- Cost optimization (LLM inference is expensive)

---

## What's NOT in This Build Plan (v2+)

- iOS IPA analysis
- Real-time network IDS deployment
- Customer-facing UI
- Mobile app
- Multi-tenant SaaS
- Federated learning across banks
- Adversarial robustness testing
- Differential privacy for shared threat intel

These are explicit out-of-scope for v1. Roadmap them in v2.

---

## Risk Register

| Risk | Mitigation |
|---|---|
| LLM hallucinations in synthesis | Debate layer, grounding in tool outputs, human review for CRITICAL |
| GPU costs for 70B+ models | Offer smaller model variants, cloud GPU for synthesis only |
| Neo4j becomes bottleneck | NebulaGraph migration path designed |
| Malicious APK escapes sandbox | Network isolation, no internet access for analysis workers |
| Adversarial input to LLM (prompt injection in decompiled code) | Treat decompiled code as data, not instructions; use structured outputs |
| Bank compliance varies | Configurable per-deployment, audit trail mandatory |
| Open-source tool stops being maintained | Pin versions, fork critical deps, build relationships |

---

## Success Definition

PARALLAX v1 is "flagship product" when:

1. ✅ Processes 100+ APKs/day with <12 min latency
2. ✅ >99% detection on known malware
3. ✅ >85% detection on novel variants
4. ✅ <2% false positive rate
5. ✅ Auto-generates YARA rules that catch new samples
6. ✅ Produces STIX 2.1 output compatible with MISP/OpenCTI
7. ✅ Attribution accuracy improves with each APK
8. ✅ Three pilot banks using it for production decisions
9. ✅ Threat intel shared with at least one peer bank via MISP
10. ✅ Measurably self-improves over time (proven via metrics)

---

*Next: See supporting docs `05_API_DESIGN.md`, `06_TAIG_SCHEMA.md`, `07_AGENT_PROMPTS.md`, `08_TESTING_STRATEGY.md`, `09_DEPLOYMENT.md`, `10_INNOVATION_LOG.md` (all in PSBs folder).*
