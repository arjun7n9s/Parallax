# PARALLAX — Build Handoff & Resume Guide

**Session date:** 2026-06-12
**Status at halt:** Clean checkpoint. All tests green, mypy clean, ruff clean. **Nothing committed yet** (work is in the working tree).
**Purpose of this doc:** Capture exactly what was built, the current runtime state, how to resume, and what's left — so the build can pick up cold after a break.

---

## 1. What PARALLAX is (one paragraph)

A GenAI-native Android banking-malware analysis platform that acts as an **AI investigator** rather than a tool-runner: it forms hypotheses, picks tools, reads decompiled code, drives the app at runtime, reconstructs the fraud attack chain, and produces an evidence-first report with an auditable two-layer risk score. Every analyzed APK enriches a shared knowledge graph (TAIG) so detection compounds over time. Operative plan: **`Plan/04b_INTEGRATED_BUILD_ORDER.md`** (anchor: `Plan/PARALLAX_VISION.md`). The `Other-Plans/` folder is **out of scope** — ignore it.

---

## 2. Where the build was before this session

Already existed and tested (Phases 0–3 partial): ingestion → triage → static → dynamic worker chain, API + DB models + migrations, static engine (androguard/jadx/YARA/FlowDroid runner), hook planner, AVD manager, Frida + mitmproxy + DroidBot, hypothesis engine. **The "brain, memory, and outputs" (~40%) were missing** — the dynamic worker handed off to a `reasoning` state that nothing consumed, and Neo4j/Qdrant were provisioned but unused.

## 3. What this session built

### Foundation
- **`parallax/parallax/ai/llm.py`** — unified LLM provider. Role→model roster; routes to local Ollama now and Anthropic/OpenAI when `LLM_MODE=cloud|auto` and a key is set. JSON + text + vision + embeddings. Cloud SDKs lazy-imported.
- Environment wiring: `JADX_BIN`, `FLOWDROID_JAR`, cloud keys, dynamic-device flags, webhook + threat-intel settings added to **`core/config.py`** and **`.env`**.

### Phase 4 — AI Reasoning Cortex (`parallax/parallax/ai/`)
- `schemas.py` — Pydantic I/O contracts for every agent + `CortexResult` (the downstream contract).
- `agents/code_interpreter.py`, `agents/behavior_analyst.py`, `agents/intel_correlator.py`, `agents/visual.py`, `agents/synthesis.py`.
- `re_workbench/code_selector.py` — ranks decompiled files by sensitive-API signal, skips framework packages, budgets the prompt (grounds the Code Interpreter in real code).
- `rag/attck.py` — curated ATT&CK Mobile catalog + embedding retrieval (prevents hallucinated technique IDs).
- `debate.py` — deterministic contradiction detection (clean-static + dirty-dynamic ⇒ evasion).
- `risk.py` — two-layer scoring (Layer A evidence score live; Layer B calibration = identity until labeled corpora).
- `orchestration.py` — runs the agent DAG (parallel fan-out → intel → debate → risk → synthesis), per-agent error isolation, IOC extraction.
- `prompts/cortex.py` — evidence-first system prompts.
- **`workers/reasoning_worker.py`** — closes the `dynamic → reasoning → complete` gap; loads real inputs (decompiled code, observations, screenshots), runs the cortex, persists verdict/score/IOCs, enriches graph + vectors + pattern memory. Wired into `dynamic_worker.py`.

### Phase 5 — TAIG knowledge graph (`parallax/parallax/knowledge/`)
- `neo4j_client.py` (async, read-only guard for hunts), `population.py` (idempotent MERGE), `qdrant_store.py` (submission embeddings + semantic search), `ioc_matcher.py` (MalwareBazaar/VT/internal-corpus family attribution — replaces Diaphora), `campaign_detection.py` (Louvain over shared C2), `pattern_memory.py` (8-category subsystem), `misp_sync.py`.
- API: `api/routes/graph.py` (`/graph/cypher|similar|find-by-ioc|patterns`), `api/routes/hunt.py` (`/hunt`, named hunts, `/hunt/detect-campaigns`).

### Phase 6 — Delivery (`parallax/parallax/delivery/`)
- `fraud_chain.py` (10-stage bank-specific chain), `report_generator.py` (HTML + reportlab PDF — WeasyPrint avoided, needs native GTK), `stix_exporter.py` (STIX 2.1), `yara_generator.py` (auto-gen + compile-validate), `fraud_rules.py` (DSL + Suricata), `webhook_dispatcher.py` (HMAC + retries), `grafana_dashboards/*.json`.
- **`workers/delivery_worker.py`** — generates all artifacts, stores in MinIO, dispatches webhooks. Triggered by the reasoning worker.
- API: `api/routes/results.py` (`/analysis/{id}/result|irt|fraud-chain|report.html|report.pdf|stix|yara|fraud-rules`).

### Phase 3 finish + fixes
- `analysis/dynamic/protocol_decoders.py` (DNS/DoH/WebSocket/gRPC), wired into `mitmproxy_runner.py`.
- DroidBot UI exploration integrated into `sandbox/runner.py` (screenshots keyed by `submission_id`); live device provisioning in `dynamic_worker.py` behind `DYNAMIC_LIVE_DEVICE`.
- **Fixed:** `triage_worker.py` fabricated fake permissions → now real androguard manifest data. `androguard_runner.py` dumped 26 MB of logs and ran full DEX analysis → now lightweight manifest-only parser, loguru silenced. **Migration `0005` had a duplicate-index bug** that failed on any fresh DB → fixed.

### Tests added
`tests/unit/test_cortex.py`, `test_protocol_decoders.py`, `test_delivery.py`; `tests/integration/test_knowledge.py` (live Neo4j, auto-skips if unreachable).

---

## 4. Current state (verified)

- **81 unit tests pass**, mypy clean (38 new files), ruff clean.
- **Live-verified individually:** LLM JSON gen (phi3), embeddings (nomic, 768-dim), Neo4j population + Qdrant similarity (0.80 match) + Louvain campaigns, full delivery pipeline (valid STIX, compiling YARA, PDF, 6-stage fraud chain), static pipeline on a real APK (`samples/deskclock.apk`).
- **Not yet demonstrated end-to-end:** a full chained multi-agent cortex run — see Known Limitation below.

### The one real limitation
A full cortex run **times out on this CPU-only machine**: a single qwen/mistral-7B call on a real decompiled-code prompt exceeds minutes (`httpx.ReadTimeout`), and the box can't hold two 7B models resident. This is **hardware, not code** — every agent is error-isolated. **Fix:** `LLM_MODE=cloud` + `ANTHROPIC_API_KEY` (credits arriving) routes heavy agents to Claude, or run on a GPU. Local Ollama timeout was raised to 900s.

### Working-tree state (uncommitted)
- 12 modified tracked files, 27 new files/dirs (full inventory in §3).
- `tools/jadx/` (local jadx install) and `samples/` (test APK + decompiled output) are **local artifacts — do not commit**; add to `.gitignore` if committing.

---

## 5. Runtime state (machine-specific)

- **Ollama** native at `C:/Users/arjun/AppData/Local/Programs/Ollama/ollama.exe`, :11434. Models pulled: `nomic-embed-text`, `phi3:mini`, `qwen2.5-coder:7b`, `mistral:7b`, `llava:7b`. **Do not start the docker `ollama` service** (port clash).
- **jadx** at `tools/jadx/bin/jadx.bat` (wired via `JADX_BIN`). FlowDroid jar present.
- **Emulator** `emulator-5554` (Android 11, x86_64, rooted, frida-server 17.11.0 running). adb at `C:/Users/arjun/AppData/Local/Android/Sdk/platform-tools/adb.exe` (use `MSYS_NO_PATHCONV=1` for remote paths).
- **Data services** running via `docker compose up -d postgres redis minio neo4j qdrant`. Schemas initialized; Postgres at migration head `0005`. (Neo4j/Qdrant/Postgres/Redis/MinIO were up at halt; they may need restarting after the break.)
- venv: `parallax/.venv/Scripts/python.exe`. Run scripts with `PYTHONPATH=.` or via stdin heredoc.

---

## 6. How to resume (cold-start checklist)

```bash
cd "C:/Users/arjun/Desktop/PSBs/GenAI-Cybersec-hackathon/parallax"

# 1. Bring infra back up (skip ollama service — use native)
docker compose up -d postgres redis minio neo4j qdrant

# 2. Confirm native Ollama is serving
curl -s http://localhost:11434/api/version

# 3. (If DB was reset) re-init schemas + migrations
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe scripts/init_neo4j.py
.venv/Scripts/python.exe scripts/init_qdrant.py

# 4. Sanity: full green check
.venv/Scripts/python.exe -m pytest tests/unit -p no:cacheprovider -p no:warnings -q
.venv/Scripts/python.exe -m ruff check parallax/
.venv/Scripts/python.exe -m mypy parallax/ai parallax/knowledge parallax/delivery
```

When the **Anthropic key** is available, set in `parallax/.env`:
```
LLM_MODE=cloud
ANTHROPIC_API_KEY=sk-ant-...
```
Then the full cortex runs fast end-to-end.

---

## 7. Next steps (priority order for resume)

1. **Run the full cortex end-to-end via cloud** (once key is in). Tune prompt quality on a real malicious sample. This is the last live verification.
2. **Get real malware samples** (MalwareBazaar/VT key or files) for true detection accuracy — only a benign APK tested so far.
3. **Wire FlowDroid taint into `static_worker.py`** and feed `taint_flows` into the Code Interpreter / Intel Correlator (runner + table already exist).
4. **Risk calibration Layer B** — train `_calibrate` in `parallax/ai/risk.py` on labeled corpora (currently identity).
5. Optional: DSPy prompt optimization; auto-provision Grafana dashboards on boot.
6. **Decide on committing** — the session's work is uncommitted. Suggested: branch + logical commits (foundation/cortex/TAIG/delivery/phase3-fixes), add `tools/` and `samples/` to `.gitignore`.

---

## 8. Memory files written (for the assistant)

`~/.claude/projects/.../memory/`: `parallax-project.md`, `parallax-environment.md`, `parallax-known-gaps.md` (indexed in `MEMORY.md`). These let a fresh session recall context automatically.
