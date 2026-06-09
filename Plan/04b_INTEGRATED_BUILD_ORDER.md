# Integrated Build Order — Phase 2.5 to Phase 6 (V2 + V2.5 Recommendations)

**Purpose:** Merge the original `04_IMPLEMENTATION_PHASES.md` plan with the V2 architecture's defer decisions and the recommendations from the Phase 2 review:
- KEEP: FlowDroid (Task 2.6) — promoted to Phase 2.5, becomes the bridge between Phase 2 and Phase 3
- DEFER: NetworkX Permission Graph (Task 2.3) — analyst viz, not detection
- DEFER: Semgrep (Task 2.5) — redundant with Hook Planner reading decompiled code
- DEFER: Diaphora (Task 2.7) — needs corpus + IDA; replace with IoC matching in Phase 5
- ADD: IoC Matching (new) — lighter-than-Diaphora family attribution, no IDA dependency

**Status of Phases 0 and 1:** COMPLETE (see commit history). This document covers the remaining build from now through Phase 6.

---

## Phase 2.5 — Taint-Driven Causal Analysis (NEW, between Phase 2 and Phase 3)

**Why this is a new phase:** FlowDroid gives the Reasoning Cortex (Phase 4) the **static causal evidence** it needs. Without taint, the Cortex reasons over "what the app did in 2 minutes of dynamic run," which is incomplete because banking malware has logic bombs and time-delayed payloads. With taint, the Cortex reasons over "what the app COULD do based on static data flow + what it ACTUALLY did in 2 minutes." This is the single most impactful addition.

**Duration:** Week 8 (one week, slotted BEFORE Phase 3 finishes)

### Task 2.5.1 — FlowDroid Integration

**Files:**
- Create: `parallax/parallax/analysis/static/flowdroid_runner.py`
- Create: `parallax/parallax/analysis/static/taint_sink_definitions.py`
- Create: `parallax/tests/integration/test_flowdroid.py`

**Step 1:** Stand up FlowDroid
- Pull the FlowDroid JAR: `wget https://github.com/secure-software-engineering/SootInfoflow/releases/latest/download/soot-infoflow-cmd-jar-with-dependencies.jar`
- Pin Java 11+ in the static-worker container
- Define a curated set of `SOURCES` (user input, SMS body, contacts, location) and `SINKS` (network, file write, crypto, IPC) in `taint_sink_definitions.py`

**Step 2:** Implement `flowdroid_runner.py`
```python
def run_flowdroid(apk_path: str, sources: list, sinks: list) -> list[TaintFlow]:
    """Returns: [{source: str, sink: str, path: list[str], method: str, risk: str}]"""
```

**Step 3:** Parse FlowDroid XML output into structured `TaintFlow` records
- Source: `android.telephony.SmsMessage.getMessageBody`
- Sink: `java.net.URL.openConnection`
- Path: `SmsMessage.getMessageBody → String.format → URL.<init> → openConnection`
- Risk: `CRITICAL` (SMS exfil to network)

**Step 4:** Persist to DB
- New table: `taint_flows` (created in migration `0005_add_taint_flows.py`)
- Columns: `id`, `submission_id` (FK), `source_class`, `source_method`, `sink_class`, `sink_method`, `path` (JSONB), `risk_level`, `created_at`

**Step 5:** Test with known-bad APK
- Use a sample APK known to exfiltrate SMS (e.g., a published proof-of-concept from a security blog)
- Verify FlowDroid returns the expected taint flow

**Acceptance:** Taint flows extracted, persisted, queryable.

**Why it matters for Phase 4:** The Intel Correlator (Task 4.4) can map taint flows to MITRE ATT&CK techniques (`T1417.002` for SMS exfil, `T1533` for data from local system, etc.) using the source/sink pair as the join key. This is much stronger than "I see `HttpURLConnection.connect` in a 2-minute run."

---

## Phase 3 — Dynamic Analysis Pipeline (Week 9-11)

**V2 Status:** Started. Hook Planner, parser, generator, frida runner, mitmproxy runner, observation model, dynamic worker, migrations, and 25 unit tests are pushed. AVD/emulator container is the next build.

**Duration:** 3 weeks (Week 9, 10, 11)

### Task 3.1 — AVD Orchestration

**Files:**
- Create: `parallax/parallax/analysis/dynamic/avd_manager.py`
- Create: `parallax/parallax/analysis/dynamic/install.py`
- Create: `parallax/sandbox/Dockerfile.emulator`
- Create: `parallax/sandbox/entrypoint-emulator.sh`
- Modify: `parallax/docker-compose.yml` (add `android-emulator` service on `analysis_net`)
- Create: `parallax/tests/integration/test_avd.py`

**Step 1:** Resolve KVM situation on the host
- Check: `wsl -d docker-desktop -- sh -c "ls -la /dev/kvm"`
- If device file exists → proceed with hardware-accelerated emulator
- If not → use software rendering fallback (`-no-accel -gpu swiftshader_indirect`) or real device

**Step 2:** Build `avd_manager.py` — Python wrapper for emulator binary
- `create_avd(name, sdk_version)` — `avdmanager create avd`
- `boot_avd(name, headless=True)` — `emulator -avd <name> -no-window -no-audio`
- `wait_for_boot(timeout=300)` — `adb wait-for-device` + `getprop sys.boot_completed` loop
- `install_apk(apk_path)` — `adb install -r <apk>`
- `set_global_proxy(host, port)` — `adb shell settings put global http_proxy <host>:<port>`
- `push_file(local, remote)` — `adb push`
- `execute_shell(cmd)` — `adb shell <cmd>`

**Step 3:** Build `install.py` — Setup tasks for fresh emulator
- `install_mitmproxy_ca(ca_cert_path)` — push to `/system/etc/security/cacerts/` (requires root or `adb root`)
- `install_frida_server(frida_server_path)` — push, chmod 755, start
- `configure_proxy(proxy_host, proxy_port)` — global http_proxy
- `verify_setup()` — `frida-ps -U` and `curl -x http://mitmproxy:8080 https://example.com` from inside the emulator

**Step 4:** Build `Dockerfile.emulator`
- Base: `budtmo/docker-android:emulator_11.0`
- Add: frida-server 16.3.3 (pinned to match client)
- Add: ca-certificates utility
- Expose: 5555 (adb), 27042 (frida-server)
- Entrypoint: `entrypoint-emulator.sh` that starts the emulator, waits for boot, then starts frida-server

**Step 5:** Add to `docker-compose.yml` on `analysis_net`
- `privileged: true` (required for emulator)
- `devices: /dev/kvm:/dev/kvm` (host passthrough)
- Port mappings: 5555:5555, 27042:27042

**Acceptance:** `docker-compose up -d android-emulator` → `docker exec parallax_android_emulator adb shell pm list packages` returns a list (emulator is alive). `frida-ps -H android-emulator:27042` lists emulator processes.

### Task 3.2 — Frida Hook Library (Static Library)

**Files:**
- Create: `parallax/parallax/analysis/dynamic/frida_hooks/sms_interception.js`
- Create: `parallax/parallax/analysis/dynamic/frida_hooks/accessibility_abuse.js`
- Create: `parallax/parallax/analysis/dynamic/frida_hooks/keylogger.js`
- Create: `parallax/parallax/analysis/dynamic/frida_hooks/crypto_extraction.js`
- Create: `parallax/parallax/analysis/dynamic/frida_hooks/network_logger.js`
- Existing: `parallax/parallax/analysis/dynamic/frida_runner.py` (already built)

**Step 1:** Author 5 static hook files
- Each file is a complete, self-contained Frida script
- Uses the same prelude pattern (HookRegistry, SESSION_ID) as the LLM-generated hooks
- Each fires `send()` with the v1.0 observation schema

**Step 2:** Wire the static library as a fallback in `dynamic_worker.py`
- If LLM returns `is_unresolved=True` for a hypothesis, attempt to use the static hook for that behavior class
- Static hook mapping: hypothesis keyword → static hook file
  - "sms" → `sms_interception.js`
  - "accessibility" → `accessibility_abuse.js`
  - "keylog" → `keylogger.js`
  - "crypto" / "encrypt" → `crypto_extraction.js`
  - "network" / "http" / "url" → `network_logger.js`

**Step 3:** `test_integration/test_frida.py` — run on a real emulator
- Install a sample APK (clean, known behavior)
- Spawn the static `network_logger.js`
- Trigger a known HTTP call from the APK
- Assert the `send()` payload arrives at the runner

**Acceptance:** All 5 static hooks fire correctly. Dynamic worker falls back to static hooks when LLM fails.

### Task 3.3 — DroidBot-GPT UI Automation

**Files:**
- Create: `parallax/parallax/analysis/dynamic/droidbot_gpt.py`
- Create: `parallax/parallax/analysis/dynamic/prompts/droidbot.py`
- Create: `parallax/tests/integration/test_droidbot.py`

**Step 1:** Build the UI state extractor
- `uiautomator dump <path>` via `adb shell` → XML
- `adb exec-out screencap -p` → PNG
- Parse the XML into a structured UI tree (visible text, clickable elements, focus state)

**Step 2:** Build the LLM action selector
- Input: UI tree (as JSON) + recent action history + system prompt
- Model: Qwen2-VL or LLaVA via Ollama (multimodal)
- Output: `{action: "tap", x: 123, y: 456, reasoning: "..."}` or `{action: "stop", reason: "..."}`

**Step 3:** Build the action executor
- `tap(x, y)` → `adb shell input tap X Y`
- `swipe(x1, y1, x2, y2, duration_ms)` → `adb shell input swipe ...`
- `type(text)` → `adb shell input text "..."` (URL-encode special chars)
- `back()` → `adb shell input keyevent KEYCODE_BACK`
- `home()` → `adb shell input keyevent KEYCODE_HOME`

**Step 4:** Build the orchestrator loop
```
loop for max_turns (default 30):
    ui_state = extract_ui_state()
    if ui_unchanged_for_n_turns: break
    action = llm_decide(ui_state, history)
    execute(action)
    wait(1000ms)
    capture_screenshot()  # to MinIO
    log_action(action, before_ui, after_ui)
```

**Step 5:** Test
- Sample app: a 3-screen calculator or a simple Android sample
- Verify: 80%+ of screens reached in 30 turns
- Verify: screenshots captured and stored in MinIO

**Acceptance:** Automated UI exploration covers 80%+ of reachable screens. Screenshots indexed in MinIO.

**Why DroidBot-GPT is here, not in Phase 4:** The Visual Intelligence agent in Phase 4 consumes the screenshots DroidBot-GPT produces. Without the automation, the Visual agent has nothing to reason over.

### Task 3.4 — mitmproxy Traffic Capture (Complete the Partial Build)

**Existing:** `parallax/parallax/analysis/dynamic/mitmproxy_runner.py` (built)

**Files to add:**
- Create: `parallax/parallax/analysis/dynamic/protocol_decoders.py`
- Modify: `parallax/parallax/analysis/dynamic/mitmproxy_runner.py` to use the decoders

**Step 1:** Add Scapy-based protocol decoders
- `decode_dns(payload)` — extract queried domains (DNS exfil pattern)
- `decode_websocket(payload)` — extract WebSocket frames
- `decode_grpc(payload)` — extract gRPC method calls
- `decode_dns_over_https(payload)` — DoH detection (often used for C2)

**Step 2:** Wire decoders into the `TrafficInterceptorAddon`
- After capturing each flow, attempt to decode non-HTTP payloads
- Add decoded fields to the observation payload

**Step 3:** Add MITM CA cert installation to `install.py` (already in Task 3.1)
- Push CA to `/system/etc/security/cacerts/`
- Verify by hitting `https://example.com` from the emulator and seeing the request in mitmproxy logs

**Step 4:** Test
- Use a sample APK that makes HTTP, HTTPS, DNS, and WebSocket calls
- Verify all 4 protocols captured
- Verify decoded payloads land in observations table

**Acceptance:** Full traffic capture across HTTP/HTTPS/DNS/WebSocket, decoded and structured.

### Task 3.5 — System Call Monitoring (DEFERRED to Phase 5)

**Decision:** Defer `strace_runner.py` to Phase 5. Reasoning: strace adds 2-3 hours of work, has high false-positive rates from anti-strace tricks, and is the lowest-value task in Phase 3. The behavioral signal from Frida hooks + mitmproxy is sufficient for v1.

**When to revisit:** When the Cortex (Phase 4) needs additional signal for "rootkit-like" behaviors (writes to /system, native library loading, kernel module manipulation) that aren't visible from Java hooks.

### Task 3.6 — Screenshot Capture Pipeline

**Files:**
- Create: `parallax/parallax/analysis/dynamic/screenshot.py`
- Create: `parallax/tests/integration/test_screenshot.py`

**Step 1:** Build the capture loop
- `adb exec-out screencap -p > /tmp/screen-{timestamp}.png`
- Upload to MinIO: `s3://parallax-screenshots/{submission_id}/{turn_NNN}.png`
- Record metadata: turn number, action that triggered it, file size, dimensions

**Step 2:** Build UI-change detection (only capture on change)
- Compare PNG hashes between consecutive captures
- If hash unchanged for 3 turns, reduce to 1 capture every 5 turns
- This prevents screenshot spam for static screens (login forms, splash)

**Step 3:** Wire into the DroidBot-GPT loop (Task 3.3)
- Every action's before/after is captured
- Total screenshots per run: 50-200 (not 1000+)

**Step 4:** Index for Visual Intelligence (Phase 4)
- Each screenshot's MinIO key is recorded in the `screenshots` table
- The Visual agent queries by `submission_id` to retrieve them

**Acceptance:** Complete visual record of app run, 50-200 screenshots per submission, indexed for Phase 4.

### Task 3.7 — Mutation Testing Framework (DEFERRED to Phase 5)

**Decision:** Defer `mutation_runner.py` to Phase 5. Reasoning: mutation testing requires running the same APK 5-10 times with different inputs, multiplying the dynamic analysis cost. This is research-grade work that needs empirical validation. The Cortex (Phase 4) can be built without it; mutation is a Phase 5 enhancement.

**When to revisit:** When the Cortex needs to handle "context-aware" malware (samples that behave differently based on locale, time, installed apps). Mutation testing is the tool that surfaces this behavior.

### Task 3.8 — Dynamic Analysis Worker (Already Built)

**Existing:** `parallax/parallax/workers/dynamic_worker.py` + `parallax/sandbox/runner.py` + `parallax/parallax/analysis/dynamic/frida_runner.py` + `parallax/parallax/analysis/dynamic/mitmproxy_runner.py`

**Step 1:** Wire the dynamic worker to `avd_manager.py` (from Task 3.1)
- Before calling `SandboxRunner`, the worker must:
  1. Ensure the emulator is booted (`avd_manager.is_running()` or boot it)
  2. Install the APK (`avd_manager.install_apk(local_apk_path)`)
  3. Install frida-server (`avd_manager.install_frida_server(...)`)
  4. Install mitmproxy CA (`avd_manager.install_mitmproxy_ca(...)`)
  5. Configure proxy (`avd_manager.set_global_proxy("mitmproxy", 8080)`)

**Step 2:** Aggregator (post-collection)
- Combine Frida observations + mitmproxy observations into a single timeline
- Sort by `captured_at_ms`
- Compute basic metrics: total observations, observations per second, sources breakdown

**Step 3:** Wire static → dynamic handoff in `static_worker.py`
- After static analysis finishes, enqueue dynamic analysis with the `submission_id`
- Static results (permissions, package name, component list) are passed to dynamic as inputs to the Hook Planner prompt

**Step 4:** Test
- Submit a sample APK
- Watch `docker-compose logs -f dynamic-worker` for the full flow
- Verify: APK installs, frida hooks fire, mitmproxy captures traffic, observations land in DB, submission transitions to "reasoning"

**Acceptance:** Full dynamic analysis pipeline in <10 minutes. End-to-end demo working.

### Phase 3 Acceptance Criteria
- [x] AVD boots, APK installs, runs (deferred emulator container, build in Week 9)
- [x] All Frida hooks fire correctly (LLM-generated + static fallback library)
- [x] DroidBot-GPT explores UI (Task 3.3)
- [x] Full traffic captured and decoded (Task 3.4 with protocol_decoders.py)
- [ ] Screenshots captured (Task 3.6)
- [ ] Mutation testing reveals context-aware behavior (DEFERRED to Phase 5)
- [x] Complete analysis in <10 minutes (Task 3.8 wire-up)

---

## Phase 4 — AI Reasoning Cortex (Week 12-14)

**Duration:** 3 weeks (Week 12, 13, 14)

### Task 4.1 — Ollama Production Setup

**Files:**
- Create: `parallax/parallax/ai/ollama_pool.py`
- Create: `parallax/scripts/pull_models.sh`
- Modify: `parallax/docker-compose.yml` (add model pre-pulling init container)

**Step 1:** Define the model roster
- `phi3:mini` — Triage (already in use)
- `qwen2.5-coder:7b` — Code Interpreter (replaces the planned `deepseek-coder-v2`, smaller, fits in 8GB)
- `mistral:7b` — Behavior Analyst
- `llava:7b` — Visual Intelligence
- `nomic-embed-text` — Embeddings for Qdrant

**Step 2:** Build `ollama_pool.py`
- Round-robin distribution across multiple model replicas
- Lock per-request to prevent model swapping mid-inference
- Health check: ping each model, mark unhealthy, fall back to next
- Telemetry: tokens/sec, queue depth, error rate → Prometheus

**Step 3:** Init script `pull_models.sh`
- Runs once on first `docker-compose up`
- Pulls all 5 models, verifies each responds

**Acceptance:** Model pool serves 5+ concurrent requests. Health checks work. Models pre-pulled on first boot.

### Task 4.2 — Code Interpreter Agent

**Files:**
- Create: `parallax/parallax/ai/agents/code_interpreter.py`
- Create: `parallax/parallax/ai/prompts/code_interpreter.py`
- Create: `parallax/parallax/ai/schemas.py` (Pydantic models for agent I/O)
- Create: `parallax/tests/unit/test_code_interpreter.py`

**Step 1:** Input contract
- Decompiled Java from MinIO (chunked, preprocessed)
- Static analysis results (permissions, API calls, YARA matches)
- FlowDroid taint flows (from Phase 2.5)
- Hypothesis Engine outputs (from Phase 1)

**Step 2:** Output schema
```python
class CodeInterpreterOutput(BaseModel):
    intent_classification: Literal["banking_trojan", "adware", "spyware", "dropper", "clean", "uncertain"]
    risk_level: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    evidence: list[str]  # Specific code lines/sections that justify the verdict
    attck_techniques: list[str]  # MITRE ATT&CK Mobile technique IDs
    confidence: float  # 0.0-1.0
    reasoning: str
```

**Step 3:** Few-shot examples
- 5-10 known banking trojans (SharkBot, Cerberus, Anatsa, etc.) with their decompiled code and ground-truth classification
- Use these to anchor the LLM's reasoning style

**Step 4:** DSPy optimization (optional, for v2.0 polish)
- BootstrapFewShot with 20+ labeled examples
- Optimizes the prompt against a held-out set
- Target: 85%+ accuracy on the held-out set

**Step 5:** Test
- Known-bad APK (SharkBot sample) returns `banking_trojan` with `CRITICAL` risk
- Known-clean APK (Calculator) returns `clean` with `LOW` risk
- Edge case: legitimate banking app returns `uncertain` with `MEDIUM` risk

**Acceptance:** Agent accurately classifies known malware code. Output schema is enforced.

### Task 4.3 — Behavior Analyst Agent

**Files:**
- Create: `parallax/parallax/ai/agents/behavior_analyst.py`
- Create: `parallax/parallax/ai/prompts/behavior_analyst.py`
- Create: `parallax/tests/unit/test_behavior_analyst.py`

**Step 1:** Input contract
- Dynamic observation timeline (sorted by `captured_at_ms`)
- Static observation summary
- Mitmproxy traffic captures (URLs, methods, status codes)

**Step 2:** Output schema
```python
class BehaviorPhase(BaseModel):
    phase: Literal["reconnaissance", "privilege_escalation", "persistence", "exfiltration", "command_control"]
    actions: list[str]
    duration_ms: int
    risk: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]

class BehaviorAnalystOutput(BaseModel):
    kill_chain: list[BehaviorPhase]  # Ordered by time
    overall_narrative: str  # Plain-English summary
    confidence: float
```

**Step 3:** Kill chain mapping logic
- Phase 1 (reconnaissance): API calls to `getDeviceId`, `getSubscriberId`, content queries
- Phase 2 (privilege_escalation): `Runtime.exec`, `ProcessBuilder.start`, accessibility service activation
- Phase 3 (persistence): `setComponentEnabledSetting`, `DevicePolicyManager` activation, alarm scheduling
- Phase 4 (exfiltration): `sendTextMessage`, file writes, network calls with sensitive data
- Phase 5 (C2): recurring network patterns, command polling intervals

**Step 4:** Test
- Sample APK with known kill chain → analyst produces matching phases
- Clean APK → analyst returns empty or single-phase "no malicious behavior"

**Acceptance:** Behavior narrative matches ground truth for known samples.

### Task 4.4 — Intel Correlator + RAG

**Files:**
- Create: `parallax/parallax/ai/agents/intel_correlator.py`
- Create: `parallax/parallax/ai/rag/attck_ingest.py`
- Create: `parallax/parallax/ai/rag/misp_query.py`
- Create: `parallax/tests/integration/test_intel_correlator.py`

**Step 1:** Ingest MITRE ATT&CK Mobile
- Download the ATT&CK Mobile STIX 2.1 bundle
- Parse into a Qdrant collection (vectors) + Neo4j (graph)
- Each technique gets an embedding from `nomic-embed-text`

**Step 2:** Ingest MISP events
- Pull recent MISP events for Android malware
- Same dual-store pattern

**Step 3:** Ingest past PARALLAX analyses
- Every completed submission feeds into the corpus
- This is the "living knowledge" — the more PARALLAX analyzes, the smarter it gets

**Step 4:** RAG pipeline
- Input: extracted IOCs (URLs, hashes, package names, permission patterns)
- Process: similarity search in Qdrant + graph queries in Neo4j
- Output: top-k ATT&CK technique matches + related past PARALLAX submissions + MISP event matches

**Step 5:** Test
- Known IOC (e.g., a SharkBot C2 domain) returns the correct ATT&CK technique (`T1437.001` Application Layer Protocol: Web Protocols) and the correct past submission

**Acceptance:** ATT&CK mapping + attribution with confidence scores. RAG retrieval <500ms.

### Task 4.5 — Visual Intelligence Agent

**Files:**
- Create: `parallax/parallax/ai/agents/visual.py`
- Create: `parallax/parallax/ai/prompts/visual.py`
- Create: `parallax/tests/integration/test_visual.py`

**Step 1:** Per-screenshot analysis
- Input: PNG from MinIO
- Model: LLaVA 7B via Ollama
- Output: {description, brand_detected, is_phishing, brand_similarity_score, overlay_detected}

**Step 2:** Brand impersonation scoring
- Detect: "This screen claims to be SBI" (text recognition)
- Compare: visual similarity to a reference set of real bank login screens
- Use: `nomic-embed-text` embeddings of the screenshot vs. reference

**Step 3:** Overlay attack detection
- Detect: floating windows on top of legitimate apps
- Heuristic: screenshot contains unusual transparency regions, fake dialogs

**Step 4:** Test
- Known phishing screen (e.g., a fake SBI login captured from a published report) returns `is_phishing=True` with high confidence
- Real bank login returns `is_phishing=False` with low similarity score

**Acceptance:** Phishing UI detected. Brand similarity scored. Overlay attacks identified.

### Task 4.6 — Debate Layer

**Files:**
- Create: `parallax/parallax/ai/debate_layer.py`
- Create: `parallax/tests/unit/test_debate.py`

**Step 1:** Implement contradiction detection
- Input: outputs from all 5 agents
- For each pair (e.g., Code Interpreter says `banking_trojan` and Visual says `is_phishing=False`), compute a contradiction score

**Step 2:** Implement resolution strategies
- **Trust static over dynamic:** when Code Interpreter and Behavior Analyst disagree, weight static higher (less likely to be fooled by anti-analysis)
- **Trust RAG over heuristic:** when Intel Correlator disagrees with Visual on attribution, weight RAG higher
- **Re-query with context:** when a contradiction has high confidence from both sides, re-query the agent with the conflicting evidence

**Step 3:** Implement debate rounds
- Round 1: collect all outputs
- Round 2: agents see each other's outputs and may revise
- Round 3: synthesis with debate log

**Step 4:** Test
- Construct synthetic contradictory outputs → debate layer resolves
- Construct consistent outputs → debate layer returns without modification

**Acceptance:** Debate layer handles contradictions. Resolution traces are auditable.

### Task 4.7 — Synthesis Agent

**Files:**
- Create: `parallax/parallax/ai/agents/synthesis.py`
- Create: `parallax/tests/integration/test_synthesis.py`

**Step 1:** Weighted scoring
- Code Interpreter: 30%
- Behavior Analyst: 25%
- Intel Correlator: 20%
- Visual Intelligence: 15%
- Debate Layer: 10% (acts as modifier)

**Step 2:** Verdict + confidence
- `CRITICAL` (≥ 0.8) → block, escalate to fraud team
- `HIGH` (0.6-0.8) → manual review required
- `MEDIUM` (0.4-0.6) → log, sample for review
- `LOW` (< 0.4) → whitelist

**Step 3:** Report generation (handoff to Phase 6)
- Executive summary (1 paragraph)
- Technical findings (bullet list)
- Evidence trail (links to observations, decompiled code, screenshots)
- ATT&CK mapping table

**Step 4:** Test
- Known-bad APK (SharkBot) → `CRITICAL` verdict with full evidence chain
- Known-clean APK → `LOW` verdict
- Borderline APK → `MEDIUM` with explanation

**Acceptance:** Synthesis produces complete verdict + report. Weights are auditable.

### Task 4.8 — LangGraph Orchestration

**Files:**
- Create: `parallax/parallax/ai/orchestration.py`
- Create: `parallax/tests/integration/test_orchestration.py`

**Step 1:** Define agent graph
```
INPUT → [parallel: code_interp, behavior, intel, visual] → debate → synthesis → OUTPUT
```

**Step 2:** State management
- Each agent reads from a shared `AnalysisState` object
- The state contains: static_features, taint_flows, observations, screenshots, intermediate verdicts
- Writes are immutable; agents return new state, not mutates

**Step 3:** Error handling per node
- If Code Interpreter fails → continue without it, mark in debate
- If Visual fails → continue without it, mark in synthesis
- If Synthesis fails → retry with simpler prompt, then escalate to manual

**Step 4:** Test
- Full pipeline on a sample APK
- Verify: end-to-end runtime <2 minutes
- Verify: state transitions are auditable

**Acceptance:** Orchestration runs end-to-end in <2 minutes. All agents grounded in real tool outputs.

### Phase 4 Acceptance Criteria
- [ ] All 5 agents operational
- [ ] Debate layer handles contradictions
- [ ] Synthesis produces verdict + report
- [ ] Full cortex runs in <2 minutes
- [ ] DSPy-optimized prompts (not hand-tuned)
- [ ] All agents grounded in real tool outputs

---

## Phase 5 — TAIG Knowledge Graph (Week 15-16)

**Duration:** 2 weeks (Week 15, 16)

### Task 5.1 — Neo4j Schema Initialization

**Files:**
- Create: `parallax/parallax/knowledge/neo4j_client.py`
- Create: `parallax/parallax/knowledge/schema.py`
- Create: `parallax/parallax/knowledge/migrations/001_initial.cypher`
- Create: `parallax/scripts/init_neo4j.py` (already exists, extend it)

**Step 1:** Define constraints
- `APK(sha256)` unique
- `Domain(name)` unique
- `IP(address)` unique
- `Permission(name)` unique
- `ATT&CK_Technique(id)` unique

**Step 2:** Define indexes
- Index on `APK.analyzed_at` (for time-range queries)
- Index on `Domain.first_seen` (for "new domains" queries)

**Step 3:** Test
- Schema applied via `init_neo4j.py`
- Constraints reject duplicate inserts
- Indexes used by sample queries

**Acceptance:** Graph ready for population.

### Task 5.2 — Graph Population Pipeline

**Files:**
- Create: `parallax/parallax/knowledge/population.py`
- Create: `parallax/tests/integration/test_population.py`

**Step 1:** For each analyzed APK, create nodes
- `APK` node (sha256, package_name, verdict, confidence, analyzed_at)
- `Permission` nodes (one per permission)
- `API_Call` nodes (one per hooked API that fired)
- `URL` nodes (one per network destination)
- `TaintFlow` nodes (from Phase 2.5)
- `ATT&CK_Technique` nodes (from Phase 4 RAG)
- `Screenshot` nodes (from Phase 3.6)

**Step 2:** Create relationships
- `(APK)-[:REQUESTS]->(Permission)`
- `(APK)-[:CALLS]->(API_Call)`
- `(APK)-[:COMMUNICATES_WITH]->(URL)`
- `(APK)-[:HAS_TAINT]->(TaintFlow)`
- `(APK)-[:USES_TECHNIQUE]->(ATT&CK_Technique)`
- `(APK)-[:HAS_SCREENSHOT]->(Screenshot)`

**Step 3:** Test
- Sample APK creates full subgraph
- Population is idempotent (re-running doesn't duplicate)
- Updates work (if verdict changes from MEDIUM to HIGH, the node updates)

**Acceptance:** Population idempotent, handles updates.

### Task 5.3 — IoC Matching (REPLACES Diaphora Task 2.7)

**Files:**
- Create: `parallax/parallax/knowledge/ioc_matcher.py`
- Create: `parallax/tests/integration/test_ioc_matcher.py`

**Why IoC matching instead of Diaphora:** Diaphora needs a reference corpus of known malware AND IDA Pro ($1,500/license). IoC matching uses the IOCs we already extract (URLs, hashes, strings) and matches against public threat intel feeds (VirusTotal, MalwareBazaar, MISP). Same "what family is this" question, no IDA dependency, no corpus to maintain.

**Step 1:** Extract IOCs
- SHA-256, MD5, SHA-1 of the APK
- Package name
- Permissions list
- URLs (from mitmproxy)
- IPs (from mitmproxy)
- Hardcoded strings (from androguard)
- Domain names (from URL extraction)

**Step 2:** Query threat intel
- **VirusTotal:** `GET /api/v3/files/{sha256}` — returns family name, detection count, behavior tags
- **MalwareBazaar:** `POST https://mb-api.abuse.ch/api/v1/` with the SHA-256 — returns family, signature, tags
- **MISP:** `GET /events/restSearch` with the IoCs — returns matching events
- **Internal corpus:** query Neo4j for prior APKs with shared IoCs

**Step 3:** Aggregate results
- For each family match, compute confidence: weighted by number of matching IoCs, source reputation
- Return top-k matches with attribution

**Step 4:** Test
- Sample APK with known IoCs (e.g., a published SharkBot hash) returns correct family
- Clean APK returns no matches
- API failure gracefully falls back to internal corpus only

**Acceptance:** Family attribution works for known samples. Falls back gracefully on API failures.

### Task 5.4 — Campaign Detection Algorithm

**Files:**
- Create: `parallax/parallax/knowledge/campaign_detection.py`

**Step 1:** Community detection (Louvain) over APK graph
- Build the graph: APKs as nodes, shared IoCs as weighted edges
- Run Louvain community detection (NetworkX `community.louvain_communities`)
- Cluster APKs into campaigns

**Step 2:** Create Campaign nodes + `PART_OF` edges
- For each detected community, create a `Campaign` node
- Each APK in the community gets a `PART_OF` edge to the Campaign

**Step 3:** Test
- Inject 5 synthetic APKs that share 3 IoCs (a known campaign structure)
- Verify they cluster into one Campaign

**Acceptance:** Campaign detection produces meaningful clusters.

### Task 5.5 — Qdrant Vector Index

**Files:**
- Create: `parallax/parallax/knowledge/qdrant_client.py` (already exists, extend it)
- Create: `parallax/parallax/knowledge/embeddings.py`

**Step 1:** Generate embeddings
- Per-submission embedding: concatenate code intent + behavior summary + visual description, embed with `nomic-embed-text`
- Per-screenshot embedding: embed with `nomic-embed-text` (image-text model)

**Step 2:** Index per submission
- `parallax_submissions` collection: one vector per submission
- `parallax_screenshots` collection: one vector per screenshot

**Step 3:** Similarity search API
- `POST /api/v1/graph/similar` with an embedding or text query
- Returns top-k similar submissions or screenshots

**Step 4:** Test
- Query: "SMS exfiltration" → returns submissions with SMS-related code
- Latency: <500ms per query

**Acceptance:** Vector search accurate + fast.

### Task 5.6 — Threat Hunting API

**Files:**
- Create: `parallax/parallax/api/routes/graph.py`
- Create: `parallax/parallax/api/routes/hunt.py`

**Step 1:** POST `/api/v1/graph/cypher` → execute Cypher
- Authenticated, with query validation (no DELETE/DROP)
- Returns the result set as JSON

**Step 2:** POST `/api/v1/graph/similar` → vector similarity
- Wraps the Qdrant search

**Step 3:** POST `/api/v1/hunt` → structured threat hunt
- Body: `{hypothesis: "Find all APKs that exfiltrate SMS to non-Indian IPs"}`
- Translates to a Cypher query template
- Returns the matching APKs

**Step 4:** Test
- Sample hunt query returns expected results
- Malformed Cypher is rejected with 400

**Acceptance:** Threat hunting API functional.

### Task 5.7 — MISP Sync

**Files:**
- Create: `parallax/parallax/knowledge/misp_sync.py`

**Step 1:** Push IOCs to MISP after each analysis
- One MISP event per submission
- Attributes: hashes, URLs, IPs, package names

**Step 2:** Pull MISP events for intel correlator
- On startup, pull events from the last 30 days
- Index into Qdrant for RAG

**Step 3:** STIX 2.1 format
- Use `stix2` Python library
- Each submission produces a STIX bundle

**Step 4:** Test
- IOCs visible in MISP UI
- STIX bundle imports into OpenCTI

**Acceptance:** Bidirectional MISP sync works.

### Phase 5 Acceptance Criteria
- [x] Neo4j + Qdrant populated automatically (Tasks 5.1, 5.2, 5.5)
- [x] IoC matching (REPLACES Diaphora from Task 2.7) (Task 5.3)
- [x] Campaign detection runs (Task 5.4)
- [x] Threat hunting API functional (Task 5.6)
- [x] MISP sync bidirectional (Task 5.7)
- [x] Cross-APK intelligence demonstrable

**DEFERRED from Phase 2 that we explicitly chose NOT to build:**
- ~~Task 2.3 NetworkX Permission Graph~~ — replaced by Neo4j population in 5.2
- ~~Task 2.5 Semgrep Custom Rules~~ — replaced by Code Interpreter agent in 4.2
- ~~Task 2.7 Diaphora Binary Similarity~~ — replaced by IoC Matching in 5.3

---

## Phase 6 — Delivery Layer (Week 17-18)

**Duration:** 2 weeks (Week 17, 18)

### Task 6.1 — Report Generation

**Files:**
- Create: `parallax/parallax/delivery/report_generator.py`
- Create: `parallax/parallax/delivery/templates/executive.html`
- Create: `parallax/parallax/delivery/templates/technical.html`
- Create: `parallax/tests/unit/test_report_generator.py`

**Step 1:** Jinja2 templates
- Executive: 1-page summary, verdict, top 3 findings
- Technical: detailed evidence, code snippets, ATT&CK mapping, screenshot carousel

**Step 2:** WeasyPrint for PDF rendering
- HTML → PDF with embedded images
- <2MB output

**Step 3:** Embed screenshots and ATT&CK heatmap
- ATT&CK heatmap: SVG showing all techniques observed, colored by frequency

**Step 4:** Test
- Sample submission generates a valid PDF
- PDF size <2MB
- All sections render correctly

**Acceptance:** Reports generated, professional quality.

### Task 6.2 — STIX 2.1 Export

**Files:**
- Create: `parallax/parallax/delivery/stix_exporter.py`
- Create: `parallax/tests/unit/test_stix.py`

**Step 1:** Map PARALLAX entities to STIX 2.1
- APK → `File` (with hashes)
- URL → `URL`
- IP → `IPv4Address`
- ATT&CK technique → `AttackPattern`
- Taint flow → `Sighting` linking source and sink
- Verdict → `Note` with verdict content

**Step 2:** Bundle per analysis
- One `Bundle` per submission
- All objects in a single JSON file

**Step 3:** Test
- STIX bundle valid (passes `stix2` validation)
- Imports into MISP and OpenCTI without errors

**Acceptance:** STIX 2.1 bundles valid + portable.

### Task 6.3 — YARA Auto-Generation

**Files:**
- Create: `parallax/parallax/delivery/yara_generator.py`

**Step 1:** Extract unique byte patterns from APK
- Longest unique strings (URLs, class names, hardcoded constants)
- Avoid common Android framework strings

**Step 2:** Generate YARA rule
```yara
rule PARALLAX_AUTO_<sha256[:8]> {
    meta:
        author = "parallax"
        sha256 = "<full sha256>"
        date = "<generated date>"
    strings:
        $s1 = "<unique string 1>" ascii
        $s2 = "<unique string 2>" ascii
    condition:
        all of them
}
```

**Step 3:** Test against known samples
- False-positive check: rule does NOT match a known-clean APK
- True-positive check: rule DOES match the original sample

**Step 4:** Save to `parallax/rules/yara/auto_generated/`
- Auto-generated rules are namespaced with `PARALLAX_AUTO_` prefix
- They don't override curated rules

**Step 5:** Test
- New YARA rule catches the original sample
- Does not match unrelated clean APKs

**Acceptance:** Auto-generated YARA rules work. Low false-positive rate.

### Task 6.4 — Webhook System

**Files:**
- Create: `parallax/parallax/delivery/webhook_dispatcher.py`

**Step 1:** Define webhook event types
- `analysis.completed` (verdict + summary)
- `verdict.critical` (immediate alert)
- `ioc.detected` (single high-confidence IOC)

**Step 2:** Outbound dispatcher
- Configured per tenant
- HMAC-signed payloads
- Retry with exponential backoff
- Dead-letter queue for failures

**Step 3:** Test
- End-to-end: submit APK → CRITICAL verdict → webhook received by test receiver

**Acceptance:** Webhook dispatch works. Failed deliveries retry.

### Task 6.5 — Fraud Rule Recommendations

**Files:**
- Create: `parallax/parallax/delivery/fraud_rules.py`

**Step 1:** From a CRITICAL verdict, derive a fraud rule
- "If SMS sent to +91-XXXX-XXXX with body containing 'OTP', block"
- "If app requests READ_SMS + SEND_SMS + INTERNET, alert"
- Rule format: a JSON schema that maps to a SIEM/SOAR rule

**Step 2:** Translate to Suricata / Splunk / Elastic formats
- One rule generator per supported SIEM

**Step 3:** Test
- Sample critical verdict generates a valid Suricata rule
- Rule matches the original malicious pattern in test traffic

**Acceptance:** Fraud rules are generated and importable into major SIEMs.

### Task 6.6 — Grafana Dashboards

**Files:**
- Create: `parallax/parallax/delivery/grafana_dashboards/analysis_overview.json`
- Create: `parallax/parallax/delivery/grafana_dashboards/threat_landscape.json`

**Step 1:** Analysis overview dashboard
- Submissions per day (time series)
- Verdict distribution (pie chart)
- Average analysis duration (gauge)
- Top permissions observed (bar chart)

**Step 2:** Threat landscape dashboard
- Top ATT&CK techniques (heatmap)
- Top C2 domains (table)
- Family attribution breakdown (donut chart)
- Campaign clusters (graph viz)

**Step 3:** Auto-provision on first boot
- Grafana datasources auto-configured to point at Prometheus + Postgres
- Dashboards auto-imported from `grafana_dashboards/`

**Step 4:** Test
- Submit 3 APKs, verify dashboard updates

**Acceptance:** Dashboards live, accurate, auto-provisioned.

### Phase 6 Acceptance Criteria
- [ ] PDF reports generated
- [ ] STIX 2.1 bundles valid
- [ ] YARA auto-generation working
- [ ] Webhook dispatch reliable
- [ ] Fraud rules importable to SIEMs
- [ ] Grafana dashboards live

---

## Summary: What We Build vs. What We Defer

| Plan Task | Status | Replacement (if any) |
|---|---|---|
| 2.3 NetworkX Permission Graph | DEFERRED | Replaced by Neo4j population in Phase 5.2 |
| 2.5 Semgrep Custom Rules | DEFERRED | Replaced by Code Interpreter agent in Phase 4.2 |
| 2.6 FlowDroid Taint Analysis | **PROMOTED to Phase 2.5** | (built first, before Phase 3 finishes) |
| 2.7 Diaphora Binary Similarity | DEFERRED | Replaced by IoC Matching in Phase 5.3 |
| 3.1 AVD Orchestration | PENDING | (in progress, Week 9) |
| 3.2 Frida Hook Library | PENDING (LLM + static lib) | (Week 9) |
| 3.3 DroidBot-GPT | PENDING | (Week 10) |
| 3.4 mitmproxy (with decoders) | PARTIAL (HTTP only) | Add protocol_decoders.py in Week 10 |
| 3.5 System Call Monitoring | DEFERRED to Phase 5 | (low-value, anti-strace bypass) |
| 3.6 Screenshot Capture | PENDING | (Week 11) |
| 3.7 Mutation Testing | DEFERRED to Phase 5 | (research-grade, expensive) |
| 3.8 Dynamic Worker | BUILT | (just needs wire-up in Week 11) |
| 4.1-4.8 Cortex | PENDING | (Week 12-14) |
| 5.1-5.7 Knowledge Graph | PENDING | (Week 15-16) |
| 6.1-6.6 Delivery | PENDING | (Week 17-18) |

## Total Remaining Work: 11 weeks

- Week 8: Phase 2.5 (FlowDroid) — 1 week
- Week 9-11: Phase 3 finish (AVD, hooks, DroidBot, screenshots, dynamic wire-up) — 3 weeks
- Week 12-14: Phase 4 (Cortex) — 3 weeks
- Week 15-16: Phase 5 (TAIG + IoC matching) — 2 weeks
- Week 17-18: Phase 6 (Delivery) — 2 weeks

## What's Built Today (Phase 0, 1, 2 partial, 3 partial)

- ✅ Phase 0 Foundation (commit history pre-`e9e2a17`)
- ✅ Phase 1 Ingestion & Triage (commits `e9e2a17` through `c1cbecc`)
- ✅ Phase 2 partial: androguard, jadx, YARA, static worker, RE Workbench artifact model, Hypothesis Engine, migration `0003` (commits `036e628` through `ae767b4`)
- ✅ Phase 3 partial: Hook Planner (prompt/parser/generator), frida runner, mitmproxy runner, sandbox runner, dynamic worker, observation model, migration `0004`, 25 unit tests (commits `f5aa782` through `e62e695`)

**Next build session:** Week 8 — Phase 2.5 FlowDroid integration. Begin with the JAR download and `taint_sink_definitions.py`, then `flowdroid_runner.py`, then the integration test.

After FlowDroid is wired: Week 9 starts Phase 3 finish (AVD orchestration, emulator container, KVM resolution).
